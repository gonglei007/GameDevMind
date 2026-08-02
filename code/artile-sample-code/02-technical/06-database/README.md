## 数据库与中间件 — 配套代码

对应文章：二-06-游戏后端用什么数据库？MySQL／Redis／MongoDB对比

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 关系型 / 玩家存档 | `game_db.py` | SQLite 玩家表 CRUD |
| 排行榜 | `game_db.py` | 分数排行查询 |
| Redis 缓存 / MQ | 正文为 C# 骨架 | 完整 Cache-Aside 见 GameDevMind |

### 运行

```bash
python3 game_db.py
```

纯标准库（SQLite 内置），无需安装依赖。

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
