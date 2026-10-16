import contextlib
from concurrent.futures import ThreadPoolExecutor
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from game_db import ConcurrentUpdateError, GameDatabase, LeaderboardService, PlayerRepository, main


class DatabaseRegression(unittest.TestCase):
    def setUp(self):
        self.db = GameDatabase()
        self.addCleanup(self.db.close)
        self.repo = PlayerRepository(self.db)
        self.board = LeaderboardService(self.db, self.repo)

    def test_upgrade_reward_and_stale_save(self):
        player = self.repo.create_player("Alice")
        stale = self.repo.get_player(player.id)
        upgraded = self.repo.add_exp(player.id, 250)
        self.assertEqual((upgraded.level, upgraded.exp, upgraded.gold), (3, 250, 200))
        stale.gold = 999
        with self.assertRaises(ConcurrentUpdateError):
            self.repo.update_player(stale)
        self.assertEqual(self.repo.get_player(player.id).gold, 200)
        self.assertEqual(stale.version, 0)

    def test_failed_write_rolls_back_and_connection_recovers(self):
        player = self.repo.create_player("Bob")
        self.db.conn.execute("""CREATE TRIGGER reject_exp BEFORE UPDATE ON players
            WHEN NEW.exp>100 BEGIN SELECT RAISE(ABORT,'fixture rejects write'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.add_exp(player.id, 250)
        actual = self.repo.get_player(player.id)
        self.assertEqual((actual.level, actual.exp, actual.gold, actual.version), (1, 0, 100, 0))
        self.assertEqual(self.repo.add_exp(player.id, 100).gold, 150)

    def test_total_order_atomic_max_and_foreign_key(self):
        first = self.repo.create_player("first")
        second = self.repo.create_player("second")
        self.board.submit_score(second.id, 100)
        self.board.submit_score(first.id, 100)
        self.board.submit_score(first.id, 50)
        self.board.submit_score(first.id, 100)
        top = self.board.get_top()
        self.assertEqual([row["player_id"] for row in top], [first.id, second.id])
        self.assertEqual([self.board.get_player_rank(row["player_id"]) for row in top], [1, 2])
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM leaderboard").fetchone()[0], 2)
        with self.assertRaises(sqlite3.IntegrityError):
            self.board.submit_score(999999, 10)
        self.assertEqual(len(self.board.get_top()), 2)
        with self.assertRaises(ValueError):
            self.board.get_top(-1)

    def test_listing_uses_one_query_and_names_are_parameters(self):
        name = "player'); -- literal input"
        player = self.repo.create_player(name)
        self.assertEqual(self.repo.find_by_name(name).id, player.id)
        statements = []
        self.db.conn.set_trace_callback(statements.append)
        try:
            self.assertEqual(len(self.repo.list_all()), 1)
        finally:
            self.db.conn.set_trace_callback(None)
        self.assertEqual(sum(s.lstrip().upper().startswith("SELECT") for s in statements), 1)

    def test_file_reopen_concurrent_connections_and_high_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "owned-fixture.db")
            db = GameDatabase(path)
            player_id = PlayerRepository(db).create_player("persisted").id
            db.close()

            def worker(number):
                # Correctness fixture has its own bounded IO budget, not a throughput target.
                connection = GameDatabase(path, timeout=30.0)
                try:
                    repo = PlayerRepository(connection)
                    board = LeaderboardService(connection, repo)
                    for i in range(10):
                        repo.add_exp(player_id, 10)
                        board.submit_score(player_id, number * 10 + i)
                finally:
                    connection.close()

            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(worker, range(6)))
            reopened = GameDatabase(path)
            try:
                result = PlayerRepository(reopened).get_player(player_id)
                self.assertEqual((result.exp, result.level, result.gold), (600, 7, 400))
                self.assertEqual(reopened.conn.execute("SELECT score FROM leaderboard").fetchall()[0][0], 59)
                self.assertEqual(reopened.conn.execute("SELECT COUNT(*) FROM leaderboard").fetchone()[0], 1)
            finally:
                reopened.close()

    def test_busy_timeout_has_no_partial_write_and_can_recover(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "busy-fixture.db")
            holder = GameDatabase(path)
            contender = None
            try:
                player_id = PlayerRepository(holder).create_player("busy").id
                contender = GameDatabase(path, timeout=0.01)
                holder.conn.execute("BEGIN IMMEDIATE")
                with self.assertRaises(sqlite3.OperationalError) as raised:
                    PlayerRepository(contender).add_exp(player_id, 100)
                self.assertEqual(raised.exception.sqlite_errorcode & 0xFF, sqlite3.SQLITE_BUSY)
                holder.conn.rollback()
                unchanged = PlayerRepository(contender).get_player(player_id)
                self.assertEqual((unchanged.exp, unchanged.gold, unchanged.version), (0, 100, 0))
                self.assertEqual(PlayerRepository(contender).add_exp(player_id, 100).gold, 150)
            finally:
                holder.close()
                if contender is not None:
                    contender.close()

    def test_failed_legacy_migration_preserves_rows_and_version(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "legacy-fixture.db")
            legacy = sqlite3.connect(path)
            legacy.executescript("""
                CREATE TABLE _meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                INSERT INTO _meta VALUES('schema_version','2');
                CREATE TABLE players(id INTEGER PRIMARY KEY,name TEXT);
                INSERT INTO players VALUES(1,'legacy');
                CREATE TABLE leaderboard(id INTEGER PRIMARY KEY,player_id INTEGER,category TEXT,score INTEGER);
                INSERT INTO leaderboard VALUES(1,1,'default',10),(2,1,'default',20);
            """)
            legacy.close()
            with self.assertRaises(sqlite3.IntegrityError):
                GameDatabase(path)
            check = sqlite3.connect(path)
            try:
                self.assertEqual(check.execute("SELECT COUNT(*) FROM leaderboard").fetchone()[0], 2)
                self.assertEqual(check.execute("SELECT value FROM _meta").fetchone()[0], "2")
                self.assertNotIn("version", [row[1] for row in check.execute("PRAGMA table_info(players)")])
            finally:
                check.close()

    def test_demo_does_not_touch_fixed_database_file(self):
        real_connect = sqlite3.connect

        def memory_only(path, *args, **kwargs):
            # Fail BEFORE opening any file if demo regresses to a fixed on-disk path.
            self.assertEqual(path, ":memory:")
            return real_connect(path, *args, **kwargs)

        with mock.patch("game_db.sqlite3.connect", side_effect=memory_only), contextlib.redirect_stdout(io.StringIO()):
            main()
        self.assertEqual(self.db.conn.execute("SELECT value FROM _meta").fetchone()[0], "3")


if __name__ == "__main__":
    unittest.main()
