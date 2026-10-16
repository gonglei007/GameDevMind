# 数据库配套验证

对应 [数据库](../../../../mds/2.技术能力/2.2.2.数据库.md)。

| 示例 | 范围 | 边界 |
|------|------|------|
| [transaction_contract](transaction_contract/) | MySQL 8.0/InnoDB 事务、请求身份和 RC/RR 读视图 | 单数据库、单进程客户端；不包含鉴权、支付验单或外部消息投递 |
| [SQLite 存档与排行榜](../../../artile-sample-code/02-technical/06-database/) | 迁移、版本 CAS、升级奖励与唯一最高分 | Python 标准库教学，不模拟 MySQL/MongoDB 的隔离 |
| [Go 排行榜快照](../../3.研发能力/3.2.3.服务端优化/leaderboard_snapshot/) | 真实 MySQL/Redis、有界展示快照 | 不能用于权威结算 |

运行命令及未覆盖范围见各 README。测试通过不代表生产容量、故障切换或备份恢复已验证。
