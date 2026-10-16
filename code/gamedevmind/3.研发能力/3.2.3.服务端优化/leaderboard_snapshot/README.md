# Go 排行榜展示快照

对应 [服务端优化](../../../../../mds/3.研发能力/3.2.3.服务端优化.md)、[排行榜案例](../../../../../cases/leaderboard-optimization.md) 和 [AI 建议复核](../../../../../ai-cases/go-leaderboard-cache.md)。替代普通 Pipeline 删榜重建、无 TTL 和共享可变切片的旧片段。

## 范围与实现

- 数据仅为有界 TopN 展示，`power DESC, uid ASC`，uid 唯一正整数、power 非负 int64。`MaxRows=1000` 是示例保护上限，需按产品预算调整，不是容量推荐。
- `SQLLoader` 在一个 SELECT 中取一致排序，检查 Query/Scan/Rows.Err 并关闭 Rows；实际数据是否使用索引需另测执行计划。
- `Publisher.Refresh` 查询前记录源捕获起点，完整读取并校验后生成随机版本；同一发布器实例按门闩串行，等待可取消。源读取失败/过期不发布，不把部分列表当成功。
- `RedisStore.Publish` 将完整 JSON 用一个 SET 与过期时间替换；没有 DEL+ZADD 中间态。整数字段以 JSON 字符串传输，避免 double score 或浏览器数字精度损失。传输错误后的执行结果可能未知，不能保证“报错就一定没写”。
- `Reader.Get` 合并单实例并发 miss，返回独立快照切片；有效空榜可缓存，缺 key/错误返回不可用。等待者可取消，共享加载有独立超时，loader 必须遵守 context。
- L1 有效期取本地 TTL 与源截止时间的较早者；丢失通知不导致无限陈旧。缓存失效后可重取，但不会重置源截止时间。
- `Page` 对已校验快照翻页，游标包含版本与两个排序键，拒绝跨版本和无效位置；只遍历所缓存 TopN，没有实现全榜排名、任意跳页或 live SQL 一致遍历。

## 明确未实现的部分

不包含 HTTP、鉴权、权威积分写入/发奖、跨 key 总并发门禁、键数淘汰、断路器、分布式发布锁/fencing、持久化和故障切换。Redis miss 不直接查 MySQL，避免把“兜底”写成无限回源。RedisStore 每次读取整份有界快照，适配器只允许受控的小值，不是通用大对象客户端。

每个 key 必须由**单一发布者进程**负责；另一个发布者可能用旧查询覆盖新数据，本例没有解决分布式乱序。缓存 key 应隔离环境、地域、赛季、区服与权限范围。各进程需同步时钟并预留偏差预算；源捕获时间是查询起点，不是数据库提交水位，读副本延迟仍需另外控制。不能用此快照证明权威新鲜度或进行结算。

应用必须配置 Redis 客户端池/读写超时，选择是否重试并限定上限，`ContextTimeoutEnabled` 应明确设置。Reader 仅合并同一实例同一键，故障下连续新请求仍可触发后续加载；生产需配合入口/依赖并发预算和故障退避，不能据此声称 Redis 永远不会过载。

## 本地核心回归

要求 Go 1.27.2 或兼容的新版本；依赖和校验文件已提交。从仓库根目录进入本目录执行：

```bash
go mod verify
go test -v -count=1 -timeout=45s ./...
# 支持 race 的系统还需 C 编译器（CI 在 Linux 执行）：
go test -race -v -count=1 -timeout=90s ./...
```

没有服务环境变量时，真实依赖测试明确显示 SKIP；不能把这一结果称作 MySQL/Redis 已验证。其他测试覆盖精确整数、同分/跨版本游标、空榜、源截止时间、切片隔离、并发 miss 合并、取消、共享加载超时和失败发布。

## 独立服务集成回归

CI 为每次任务启动 MySQL 8.0 和 Redis 7.4 容器。仅允许独立的 `rank_regression` 数据库；测试创建唯一命名的表与 Redis key，不读取/覆盖现有业务表，不执行 DROP、DELETE 或 FLUSH。CI 容器销毁时测试数据一起释放。本地也必须使用一次性服务，不要配置生产凭据。

```bash
export SERVER_OPT_MYSQL_DSN='root:fixture-only@tcp(127.0.0.1:3306)/rank_regression?timeout=2s&readTimeout=2s&writeTimeout=2s'
export SERVER_OPT_REDIS_ADDR='127.0.0.1:6379'
export REQUIRE_SERVER_INTEGRATION=1
go test -race -v -count=1 -timeout=90s ./...
```

PowerShell 使用 `$env:变量名='值'` 设置同名变量。CI 设置 REQUIRE 后，服务配置缺失直接失败。测试验证真实 SQL 的同分次序与大整数、Redis 完整版本/TTL、失败刷新保留旧版本、并发读写不出现半榜，以及实际缓存读取。没有做生产执行计划断言、故障切换/持久化保证或吞吐压测。

产品需要按 [服务端优化：验证方法](../../../../../mds/3.研发能力/3.2.3.服务端优化.md#验证方法) 提交固定负载、原始记录、错误/源年龄、资源与单位成本，不引用旧稿 8ms / 50k QPS 当作此示例的结果。
