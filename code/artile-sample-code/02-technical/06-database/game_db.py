#!/usr/bin/env python3
"""
游戏数据库演示 — SQLite 玩家存档 + 排行榜 TOP10

纯标准库实现，模拟游戏持久化层核心：
1. 玩家存档 — 创建/读取/更新玩家数据（等级、金币、经验）
2. 排行榜 — TOP10 查询，支持按分数/等级排序
3. 数据迁移 — 版本化 schema 升级

运行：python game_db.py
"""

import sqlite3
import json
import time
import random
import os
from dataclasses import dataclass, field
from typing import Optional, List


# ══════════════════════════════════════════════
# 数据库管理
# ══════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(__file__), "game_data.db")


class GameDatabase:
    """游戏数据库封装"""

    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")  # 并发友好
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self):
        """Schema 版本化迁移"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        cur = self.conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
        row = cur.fetchone()
        current_version = int(row["value"]) if row else 0

        migrations = [
            # v1: 初始 schema
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                last_login REAL DEFAULT 0,
                created_at REAL NOT NULL,
                extra_data TEXT DEFAULT '{}'
            )
            """,
            # v2: 添加排行榜成就表
            """
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                category TEXT DEFAULT 'default',
                updated_at REAL NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(id)
            )
            CREATE INDEX IF NOT EXISTS idx_leaderboard_score
                ON leaderboard(category, score DESC)
            """,
        ]

        for v, sql in enumerate(migrations, start=1):
            if v > current_version:
                print(f"  🗄️  迁移 v{v} ...")
                self.conn.executescript(sql)
                self.conn.execute(
                    "INSERT OR REPLACE INTO _meta(key, value) VALUES('schema_version', ?)",
                    (str(v),),
                )
                self.conn.commit()
                current_version = v


# ══════════════════════════════════════════════
# 1. 玩家存档 (CRUD)
# ══════════════════════════════════════════════

@dataclass
class PlayerSave:
    """玩家存档数据"""
    id: int = 0
    name: str = ""
    level: int = 1
    exp: int = 0
    gold: int = 0
    last_login: float = 0.0
    extra_data: dict = field(default_factory=dict)


class PlayerRepository:
    """玩家数据仓库"""

    def __init__(self, db: GameDatabase):
        self.db = db

    def create_player(self, name: str) -> PlayerSave:
        """创建新玩家"""
        now = time.time()
        cur = self.db.conn.execute(
            """INSERT INTO players (name, level, exp, gold, last_login, created_at, extra_data)
               VALUES (?, 1, 0, 100, ?, ?, '{}')""",
            (name, now, now),
        )
        self.db.conn.commit()
        return self.get_player(cur.lastrowid)

    def get_player(self, player_id: int) -> Optional[PlayerSave]:
        """读取存档"""
        cur = self.db.conn.execute(
            "SELECT * FROM players WHERE id=?", (player_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return PlayerSave(
            id=row["id"],
            name=row["name"],
            level=row["level"],
            exp=row["exp"],
            gold=row["gold"],
            last_login=row["last_login"],
            extra_data=json.loads(row["extra_data"]),
        )

    def find_by_name(self, name: str) -> Optional[PlayerSave]:
        """按名字查找"""
        cur = self.db.conn.execute(
            "SELECT * FROM players WHERE name=?", (name,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self.get_player(row["id"])

    def update_player(self, player: PlayerSave):
        """更新存档"""
        self.db.conn.execute(
            """UPDATE players SET level=?, exp=?, gold=?,
               last_login=?, extra_data=? WHERE id=?""",
            (
                player.level,
                player.exp,
                player.gold,
                time.time(),
                json.dumps(player.extra_data),
                player.id,
            ),
        )
        self.db.conn.commit()

    def add_exp(self, player_id: int, amount: int) -> Optional[PlayerSave]:
        """增加经验值并自动升级"""
        p = self.get_player(player_id)
        if p is None:
            return None
        p.exp += amount
        # 自动升级：每 100 经验升一级
        new_level = 1 + p.exp // 100
        if new_level > p.level:
            p.level = new_level
            p.gold += 50 * (new_level - p.level)  # 升级奖励
        self.update_player(p)
        return p

    def list_all(self, limit: int = 20) -> List[PlayerSave]:
        """列出所有玩家"""
        cur = self.db.conn.execute(
            "SELECT * FROM players ORDER BY level DESC, exp DESC LIMIT ?",
            (limit,),
        )
        return [self.get_player(r["id"]) for r in cur.fetchall()]


# ══════════════════════════════════════════════
# 2. 排行榜 TOP10
# ══════════════════════════════════════════════

class LeaderboardService:
    """排行榜服务"""

    def __init__(self, db: GameDatabase, player_repo: PlayerRepository):
        self.db = db
        self.players = player_repo

    def submit_score(self, player_id: int, score: int, category: str = "default"):
        """提交分数到排行榜"""
        now = time.time()
        # 先查是否已有记录
        cur = self.db.conn.execute(
            """SELECT id, score FROM leaderboard
               WHERE player_id=? AND category=?""",
            (player_id, category),
        )
        row = cur.fetchone()

        if row is None:
            # 新记录
            self.db.conn.execute(
                """INSERT INTO leaderboard (player_id, score, category, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (player_id, score, category, now),
            )
        elif score > row["score"]:
            # 仅当新分数更高时更新
            self.db.conn.execute(
                "UPDATE leaderboard SET score=?, updated_at=? WHERE id=?",
                (score, now, row["id"]),
            )
        self.db.conn.commit()

    def get_top(self, n: int = 10, category: str = "default") -> list:
        """获取 TOP N 排行榜"""
        cur = self.db.conn.execute(
            """SELECT p.name, p.level, lb.score, lb.updated_at
               FROM leaderboard lb
               JOIN players p ON p.id = lb.player_id
               WHERE lb.category = ?
               ORDER BY lb.score DESC
               LIMIT ?""",
            (category, n),
        )
        return [
            {
                "rank": i + 1,
                "name": r["name"],
                "level": r["level"],
                "score": r["score"],
                "time": r["updated_at"],
            }
            for i, r in enumerate(cur.fetchall())
        ]

    def get_player_rank(self, player_id: int, category: str = "default") -> Optional[int]:
        """查询玩家当前排名"""
        cur = self.db.conn.execute(
            "SELECT score FROM leaderboard WHERE player_id=? AND category=?",
            (player_id, category),
        )
        row = cur.fetchone()
        if row is None:
            return None

        cur2 = self.db.conn.execute(
            "SELECT COUNT(*) FROM leaderboard WHERE score > ? AND category=?",
            (row["score"], category),
        )
        return cur2.fetchone()[0] + 1


# ══════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════

PLAYER_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack", "Kate", "Leo"]


def demo_save_load():
    """演示存档读写"""
    print("═══ 1. 玩家存档演示 ═══")

    db = GameDatabase()
    repo = PlayerRepository(db)

    # 创建多个玩家
    players = {}
    for name in PLAYER_NAMES[:6]:
        existing = repo.find_by_name(name)
        if existing:
            players[name] = existing
        else:
            players[name] = repo.create_player(name)
            print(f"  ✅ 创建玩家: {name}")

    # 给玩家增加经验
    print("\n  🎮 模拟游戏 ...")
    for name in ["Alice", "Bob", "Charlie"]:
        exp = random.randint(30, 200)
        p = repo.add_exp(players[name].id, exp)
        print(f"  {name}: +{exp} EXP → Lv.{p.level} ({p.exp} EXP) 💰{p.gold}G")

    # 更新 Alice 的自定义数据
    alice = repo.find_by_name("Alice")
    alice.extra_data = {"unlocked_skins": ["dragon", "phoenix"], "achievements": 5}
    repo.update_player(alice)
    print(f"  {alice.name} 额外数据: {alice.extra_data}")

    print()
    return db, repo


def demo_leaderboard(db: GameDatabase, repo: PlayerRepository):
    """演示排行榜"""
    print("═══ 2. 排行榜 TOP10 演示 ═══")

    lb = LeaderboardService(db, repo)

    # 模拟分数提交
    all_players = repo.list_all()
    print(f"  共 {len(all_players)} 名玩家\n")

    for p in all_players:
        score = random.randint(100, 10000)
        # 高分玩家多提交几次
        for _ in range(random.randint(1, 3)):
            lb.submit_score(p.id, score + random.randint(-200, 200))

    # TOP10
    top = lb.get_top(10)
    print("  🏆 排行榜 TOP10:")
    print(f"  {'排名':<6}{'名称':<12}{'等级':<6}{'分数':<10}")
    print(f"  {'─' * 34}")
    for entry in top:
        print(f"  #{entry['rank']:<5}{entry['name']:<12}Lv.{entry['level']:<4}{entry['score']:<10}")

    # 某个玩家的排名
    if all_players:
        p = all_players[0]
        rank = lb.get_player_rank(p.id)
        print(f"\n  🔍 {p.name} 当前排名: #{rank}")

    print()


def demo_schema_version():
    """展示 schema 版本"""
    print("═══ 3. Schema 版本 ═══")
    db = GameDatabase()
    cur = db.conn.execute("SELECT * FROM _meta")
    for row in cur.fetchall():
        print(f"  {row['key']}: {row['value']}")
    print()


def main():
    print("=" * 60)
    print("  游戏数据库演示 — SQLite 存档 + 排行榜")
    print("=" * 60)
    print()

    db, repo = demo_save_load()
    demo_leaderboard(db, repo)
    demo_schema_version()

    # 清理
    db.conn.close()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    print("=" * 60)
    print("  演示完成！")
    print("  核心：SQLite CRUD → 自动升级 → 排行榜 TOP10")
    print("=" * 60)


if __name__ == "__main__":
    main()
