#!/usr/bin/env python3
"""SQLite 存档与确定性排行榜教学示例；默认仅用内存，不删除任何数据库文件。

运行 python game_db.py。文件存档由调用者显式传入路径；这不是 MySQL 隔离级别模拟器。
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import random
import sqlite3
import time
from typing import Optional

DB_PATH = ":memory:"


class ConcurrentUpdateError(RuntimeError):
    """存档版本过期；调用方需重新读并重新验证业务操作。"""


class GameDatabase:
    def __init__(self, db_path: str = DB_PATH, timeout: float = 5.0):
        self.conn = sqlite3.connect(db_path, isolation_level=None, timeout=timeout)
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self._migrate()
        except BaseException:
            self.conn.close()
            raise

    @contextmanager
    def transaction(self):
        # One connection belongs to one thread. Independent writers use independent connections.
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def close(self):
        self.conn.close()

    def _migrate(self):
        # Individual execute calls stay in our explicit transaction. executescript can commit first.
        migrations = [
            ("""CREATE TABLE players (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
                level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, gold INTEGER DEFAULT 0,
                last_login REAL DEFAULT 0, created_at REAL NOT NULL,
                extra_data TEXT DEFAULT '{}')""",),
            ("""CREATE TABLE leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER NOT NULL,
                score INTEGER NOT NULL, category TEXT NOT NULL DEFAULT 'default',
                updated_at REAL NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(id))""",
             """CREATE INDEX idx_leaderboard_score
                ON leaderboard(category, score DESC, player_id ASC)"""),
            ("ALTER TABLE players ADD COLUMN version INTEGER NOT NULL DEFAULT 0",
             """CREATE UNIQUE INDEX idx_leaderboard_player_category
                ON leaderboard(player_id, category)"""),
        ]
        with self.transaction():
            self.conn.execute("CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            row = self.conn.execute("SELECT value FROM _meta WHERE key='schema_version'").fetchone()
            current = int(row["value"]) if row else 0
            if current < 0 or current > len(migrations):
                raise RuntimeError("Unsupported schema version; no automatic downgrade")
            for version, statements in enumerate(migrations, 1):
                if version <= current:
                    continue
                for statement in statements:
                    self.conn.execute(statement)
                self.conn.execute("""INSERT INTO _meta(key,value) VALUES('schema_version',?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (str(version),))
        # Existing duplicate leaderboard rows make v3 fail and roll back; no silent data deletion.


@dataclass
class PlayerSave:
    id: int = 0
    name: str = ""
    level: int = 1
    exp: int = 0
    gold: int = 0
    last_login: float = 0.0
    extra_data: dict = field(default_factory=dict)
    version: int = 0


def positive_limit(value):
    if type(value) is not int or not 1 <= value <= 1000:
        raise ValueError("limit must be an integer in [1,1000]")
    return value


class PlayerRepository:
    def __init__(self, db: GameDatabase):
        self.db = db

    @staticmethod
    def _decode(row):
        if row is None:
            return None
        return PlayerSave(id=row["id"], name=row["name"], level=row["level"], exp=row["exp"],
                          gold=row["gold"], last_login=row["last_login"],
                          extra_data=json.loads(row["extra_data"]), version=row["version"])

    def create_player(self, name: str) -> PlayerSave:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("player name is required")
        now = time.time()
        with self.db.transaction():
            cursor = self.db.conn.execute("""INSERT INTO players
                (name,level,exp,gold,last_login,created_at,extra_data)
                VALUES (?,1,0,100,?,?,'{}')""", (name, now, now))
            player_id = cursor.lastrowid
        return self.get_player(player_id)

    def get_player(self, player_id: int) -> Optional[PlayerSave]:
        return self._decode(self.db.conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone())

    def find_by_name(self, name: str) -> Optional[PlayerSave]:
        return self._decode(self.db.conn.execute("SELECT * FROM players WHERE name=?", (name,)).fetchone())

    def _write(self, player, now):
        if player.level < 1 or player.exp < 0 or player.gold < 0:
            raise ValueError("invalid player state")
        cursor = self.db.conn.execute("""UPDATE players SET level=?,exp=?,gold=?,last_login=?,
            extra_data=?,version=version+1 WHERE id=? AND version=?""",
            (player.level, player.exp, player.gold, now, json.dumps(player.extra_data), player.id, player.version))
        if cursor.rowcount != 1:
            raise ConcurrentUpdateError("player missing or version stale")

    def update_player(self, player: PlayerSave):
        now = time.time()
        with self.db.transaction():
            self._write(player, now)
        player.version += 1
        player.last_login = now

    def add_exp(self, player_id: int, amount: int) -> Optional[PlayerSave]:
        if type(amount) is not int or amount < 0:
            raise ValueError("experience amount must be a nonnegative integer")
        now = time.time()
        with self.db.transaction():
            player = self.get_player(player_id)
            if player is None:
                return None
            old_level = player.level
            player.exp += amount
            player.level = max(old_level, 1 + player.exp // 100)
            player.gold += 50 * (player.level - old_level)
            self._write(player, now)
        player.version += 1
        player.last_login = now
        return player

    def list_all(self, limit: int = 20) -> list[PlayerSave]:
        rows = self.db.conn.execute("SELECT * FROM players ORDER BY level DESC,exp DESC,id ASC LIMIT ?",
                                    (positive_limit(limit),)).fetchall()
        return [self._decode(row) for row in rows]  # One query; no N+1 reads.


class LeaderboardService:
    def __init__(self, db: GameDatabase, player_repo: PlayerRepository):
        self.db = db
        self.players = player_repo

    def submit_score(self, player_id: int, score: int, category: str = "default"):
        if type(score) is not int or score < 0 or not isinstance(category, str) or not category:
            raise ValueError("nonnegative integer score and nonempty category required")
        with self.db.transaction():
            self.db.conn.execute("""INSERT INTO leaderboard(player_id,score,category,updated_at)
                VALUES (?,?,?,?) ON CONFLICT(player_id,category) DO UPDATE
                SET score=excluded.score,updated_at=excluded.updated_at
                WHERE excluded.score > leaderboard.score""", (player_id, score, category, time.time()))

    def get_top(self, n: int = 10, category: str = "default") -> list:
        rows = self.db.conn.execute("""SELECT p.id,p.name,p.level,lb.score,lb.updated_at
            FROM leaderboard lb JOIN players p ON p.id=lb.player_id WHERE lb.category=?
            ORDER BY lb.score DESC,lb.player_id ASC LIMIT ?""", (category, positive_limit(n))).fetchall()
        return [{"rank": i + 1, "player_id": row["id"], "name": row["name"], "level": row["level"],
                 "score": row["score"], "time": row["updated_at"]} for i, row in enumerate(rows)]

    def get_player_rank(self, player_id: int, category: str = "default") -> Optional[int]:
        row = self.db.conn.execute("""SELECT 1+(SELECT COUNT(*) FROM leaderboard other
            WHERE other.category=lb.category AND (other.score>lb.score OR
                (other.score=lb.score AND other.player_id<lb.player_id))) AS ranking
            FROM leaderboard lb WHERE lb.player_id=? AND lb.category=?""", (player_id, category)).fetchone()
        return row["ranking"] if row else None


def main():
    print("SQLite 存档与排行榜演示（仅内存，不读取或删除 game_data.db）")
    db = GameDatabase()
    try:
        repo = PlayerRepository(db)
        board = LeaderboardService(db, repo)
        rng = random.Random(42)
        for name in ["Alice", "Bob", "Charlie", "Diana"]:
            player = repo.create_player(name)
            player = repo.add_exp(player.id, rng.randint(100, 300))
            board.submit_score(player.id, rng.randint(100, 1000))
            print(f"{player.name}: level={player.level}, exp={player.exp}, gold={player.gold}")
        for row in board.get_top():
            print(f"#{row['rank']} {row['name']}: {row['score']}")
        version = db.conn.execute("SELECT value FROM _meta WHERE key='schema_version'").fetchone()[0]
        print(f"schema_version={version}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
