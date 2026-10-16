## 数据库与中间件 — 配套代码

对应文章：二-06-游戏后端用什么数据库？MySQL／Redis／MongoDB对比；知识页见 [数据库](../../../../mds/2.技术能力/2.2.2.数据库.md)。

### 文章章节与示例

| 主题 | 文件 | 实际行为与边界 |
|------|------|------|
| 玩家存档 | [game_db.py](game_db.py) | 参数化 CRUD、版本 CAS、防止旧存档覆盖；add_exp 事务内计算升级与金币奖励 |
| 排行榜 | [game_db.py](game_db.py) | 玩家/类别唯一约束，单语句 UPSERT 只提高最高分，同分按 player_id 升序，列表与单人排名一致 |
| Schema 迁移 | [game_db.py](game_db.py) | 显式事务逐语句执行，版本与 schema 共同提交；旧数据重复使唯一约束失败时完整回滚，不自动删行去重 |
| 正确性回归 | [test_game_db.py](test_game_db.py) | 空库迁移、奖励、CAS、失败回滚、独立连接并发、同分与单查询列表 |
| 真正 MySQL 行为 | [事务契约](../../../gamedevmind/2.技术能力/2.2.2.数据库/transaction_contract/) | 独立真实 InnoDB 测试，不由 SQLite 代替 |
| Redis 展示缓存 | [完整快照示例](../../../gamedevmind/3.研发能力/3.2.3.服务端优化/leaderboard_snapshot/) | 单发布者 TopN，不是完整 Cache-Aside、MQ 或结算实现 |

### 运行

Python 3.11+、SQLite 3.24+，纯标准库，无需安装依赖。从本目录运行：

```bash
python game_db.py
python -m unittest discover -s . -p 'test_*.py' -v
```

也可在仓库根目录执行 `python -m unittest discover -s code/artile-sample-code/02-technical/06-database -p 'test_*.py' -v`。CI 的 Check SQLite Database Example 会在 Windows/Linux 执行。

演示固定随机种子并默认使用内存，不读取或删除目录中的 game_data.db。需要验证持久化时显式构造 `GameDatabase('自己管理的路径')`，在 finally 中 close；路径所有权和备份由调用方管理。测试只在自身创建的临时目录保存夹具。

### 事务与迁移边界

- 每个连接限单线程使用，独立线程各建连接；BEGIN IMMEDIATE 串行化写者，WAL 不意味着多写者同时提交。构造函数 timeout 默认为 5 秒，超过预算仍可能失败，需要业务端明确处理。并发正确性夹具使用独立的 30 秒 IO 预算，另有短预算 SQLITE_BUSY 失败/恢复回归；不以此声称写入容量提高。
- update_player 用 id+version 检查过期存档；add_exp 的读取、升级、奖励与写入在同一事务。重复调用 add_exp 会重复加经验，**未实现请求幂等**，不要用于直接重放权威奖励。
- 迁移版本为 3：补充存档 version 和排行榜唯一约束。旧版重复数据必须先审查并制定迁移，库不会静默删除或选取一行；未知较新版本拒绝自动降级。
- 旧版本缺失字段、超大整数、NULL 和业务类型约束仍需产品迁移设计；本例不是完整存档平台或通用迁移工具。
- 不包含 MySQL 行锁/隔离、MongoDB、Redis、支付、跨服务一致性、容量或灾备恢复；SQL 引擎差异见 [SQLite 隔离](https://www.sqlite.org/isolation.html) 与 [Python 事务控制](https://docs.python.org/3.11/library/sqlite3.html#transaction-control)。
