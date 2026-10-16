# 用 ChatGPT 设计排行榜缓存方案

> 本记录复核 AI 给出的索引、缓存一致性与 Go 代码建议。最终交付是有边界的展示快照示例与回归，不是已证明的 5 秒到 8 毫秒提速。

**证据说明（2026-10-16）：** 仓库没有原始完整会话、线上记录或工程。旧稿描述 MySQL 5.7、200 万行，配套案例却使用 MySQL 8.0、300 万行，TTL、命中率和 CPU 后值也不同。下文保留的是旧稿提示词/输出摘录，不声称逐字完整；历史性能数字和“基本直接可用”的评价已撤回。

## 背景

历史输入是 Go 排行榜查询慢、连接池耗尽、MySQL CPU 高。它们说明需要测量，但不能单凭 `type=ALL` 或 CPU 推断完整根因。新版示例统一限定 MySQL 8.0、Redis 与有界 TopN 展示；权威积分写入和发奖不进入缓存示例。

## 对话记录

### 第一轮：索引和 ZSet 建议需要版本与语义约束

旧提示词摘录：

> Go 服务 + MySQL 5.7，排行榜表 200 万行，查询 top100 耗时 5 秒。
> SQL: SELECT user_id, score, rank FROM leaderboard ORDER BY score DESC LIMIT 100
> EXPLAIN 显示 type=ALL, rows=2000000, Using filesort。
> MySQL CPU 95%。怎么优化？

旧输出建议降序索引、Redis ZSet、分页和 Redis 写缓冲，并把方向评价为“完全正确”。

**复核：不能直接接受。** 要核对 MySQL 版本对降序索引的实际支持、字段与排序规则、选择列是否被覆盖，以及缓存是否只是展示。`ZREVRANGE` 一类范围读取的成本包含返回条数，不能仅写 O(log N)；较大 int64 转 double score 还可能丢精度。把 Redis 当权威写缓冲涉及持久化、幂等、失败恢复，不是普通查询优化。[MySQL ORDER BY](https://dev.mysql.com/doc/refman/8.0/en/order-by-optimization.html)、[ZADD](https://redis.io/docs/latest/commands/zadd/)

### 第二轮：“双写就是强一致”不成立

旧提示词摘录：

> 如果直接用 ZADD 更新 Redis，MySQL 异步写的话，
> 缓存和数据库不一致怎么办？对比一下 Write-Through 和 Cache-Aside 哪种更适合。

旧输出把 Write-Through 描述为“同时写缓存+DB，强一致（事务内）”。这个分类应撤回：策略名称不提供 Redis 与 MySQL 之间的共同原子提交。依次写任一系统都有失败和重试窗口；即使用 Redis 事务也不能自动包含 MySQL。[Redis 事务范围](https://redis.io/docs/latest/develop/using-commands/transactions/)

| 可考虑的路线 | 需要补齐的契约 |
|------|------|
| DB 权威 + Cache-Aside | 回填/失效竞争、陈旧窗口、版本、负缓存与回源上限 |
| DB 权威 + 可靠事件更新缓存 | 事务提交与事件投递、幂等消费、顺序、重放和对账 |
| 有界完整展示快照 | 源捕获时间、版本、最大年龄、单发布者与整份发布 |
| 缓存/日志参与权威写入 | 明确持久性、故障模型、冲突与恢复；不能只叫 Write-Behind 就算完成设计 |

### 第三轮：二级缓存代码没有完成承诺

旧提示词摘录：

> 本地 miss 走 Redis；Redis miss 走 MySQL（理论上不应该发生）。
> 本地缓存每 5 秒从 Redis 刷新一次。
> 写入用 Write-Through：更新 Redis ZADD + 发 PubSub 通知所有实例刷新本地缓存。

旧稿的关键代码原样摘录，**仅作反例**：

```go
if cached, ok := c.local.Load(boardType); ok {
    return cached.([]RankEntry), nil
}
entries, err := c.redis.ZRevRangeWithScores(ctx, boardType, 0, 99).Result()
if err != nil {
    return nil, err
}
c.local.Store(boardType, entries)
return entries, nil
```

拒绝原因：

- `ctx` 没有作为参数或字段声明；Redis 返回条目类型不是 `[]RankEntry`，类型断言/返回值与所存数据不匹配，片段不能独立编译。
- 缺少 TTL 和源时间检查，直接返回共享切片会暴露可变数据；map 本身线程安全不代表切片内容安全。
- 没实现所称 DB 回源、刷新/关闭、错误处理或 singleflight。文字说“加了”不能作为实现证据。
- 更新路径只写 Redis 并 Publish，没有写 MySQL，不能称为 Redis+DB Write-Through。
- Pub/Sub 可能丢通知，无法单独保证所有实例更新。[Redis Pub/Sub](https://redis.io/docs/latest/develop/pubsub/)

从 `sync.Map` 换成 `map + RWMutex` 也不自动提高性能或修复上述问题；需按访问模式与共享数据所有权验证。[Go sync.Map 文档](https://pkg.go.dev/sync#Map)

## 修正后的协作流程

新的提示词：

> 展示 TopN 允许明确的源年龄上限，结算使用权威数据库。
> 请比较直接索引读、完整快照和增量 ZSet 的适用条件。
> 固定 power DESC、uid ASC，同分不漏行，int64 不经 float64。
> 示例用一个 SET 发布完整快照，禁止普通 Pipeline 删榜重建。
> L1 不延长源截止时间，返回独立切片；空榜、缺 key、取消、并发 miss 与超时分别测试。
> 不实现无限数据库回源，不声称单进程门闩能协调多个发布者。

替代代码：[leaderboard_snapshot](../code/gamedevmind/3.研发能力/3.2.3.服务端优化/leaderboard_snapshot/)。包含完整模块和锁定依赖；CI 分别运行 Go race、真实 MySQL/Redis 集成。SQL 迭代错误不发布，Redis 用单条 SET 替换有界 JSON 快照，读取校验源截止时间，同一快照内按完整顺序分页。

## 最终成果与验证边界

| 交付 | 能验证什么 | 不能推导什么 |
|------|------|------|
| 文档与案例纠错 | 索引覆盖、同分、源年龄、双写与 Pub/Sub 的边界 | 原项目真实瓶颈及提升比例 |
| Go 核心回归 | 切片隔离、空榜、超时/取消、并发 miss、分页和失败发布 | 全分布式一致性、任意数据量和吞吐 |
| 真实依赖回归 | MySQL 排序、int64 往返、Redis 整份替换与 TTL | 生产数据计划、故障切换持久性或 8ms 容量 |
| 产品验收计划 | [案例中的待执行矩阵](../cases/leaderboard-optimization.md#效果与验证) | 没有原始记录的线上“0% 超时”等结果 |

示例单发布者、有限 TopN，不包含账号权限、分布式发布协调、权威积分事务与发奖。多轮目标负载、冷缓存、热点、慢依赖、跨节点故障与成本仍需实测。

## 关键收获

1. 策略名称不能代替事务边界、源版本、陈旧预算和失败恢复。
2. AI 声称完成的能力要在可编译代码与测试中逐项核实。
3. 对话摘录、代码正确性、集成行为和产品性能分别说明证据。

## 图谱知识点映射

- [服务端优化](../mds/3.研发能力/3.2.3.服务端优化.md) — 负载、背压和容量验收
- [数据库](../mds/2.技术能力/2.2.2.数据库.md) — 索引、排序和缓存
- [数据结构](../mds/1.基础能力/1.2.2.数据结构.md) — 引用、顺序与范围读取
- [代码重构](../mds/1.基础能力/1.2.4.代码重构.md) — 缓存接口与失败路径
- [排行榜案例](../cases/leaderboard-optimization.md) — 修正方案及验证边界
