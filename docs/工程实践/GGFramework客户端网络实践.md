# GGFramework 客户端网络实践：异常反馈与重试

本篇从“请求失败后，玩家看到什么、是否重发、还能否继续操作”出发，使用 GGFramework 的现有 Demo 观察 HTTP 异常反馈，再对照独立 GGNetwork 的接口与实现。先读[客户端网络系统](../../mds/3.研发能力/3.1.4.客户端网络系统.md)中的生命周期与重试契约，可帮助区分界面交互、传输结果和业务结果。

**项目关系与复核：** GGFramework 由本知识库作者维护；本文是工程参考。2026-11-20 完成固定源码核对与 Unity 实跑，实际结果及未覆盖项见[本轮运行记录](GGFrameworkUnity验证记录.md)。共用的[适用环境](GGFramework.md#适用条件)、[源码基线](GGFramework.md#固定源码基线)和[证据分层](GGFramework.md#验证方法与证据边界)由导读统一维护。

## 适用条件

- 具备 C#、Unity 主循环和 HTTP 基础，希望研究等待反馈、业务错误、取消重试与后续恢复。
- 接受先使用本机固定响应的测试服务，不接真实账号、凭证、订单或生产服务器。

Demo 回环服务不是弱网工具；本篇也不演示帧同步、状态同步或服务端权威恢复。这些问题分别见[网络与通信](../../mds/2.技术能力/2.2.1.网络与通信.md)与[网游网络同步](../../mds/3.研发能力/3.2.2.网游网络同步.md)。

## 两条实现路径

| 对照项 | 本篇先运行的 Demo | 独立 GGNetwork |
|---|---|---|
| 源码基线 | [Demo `e2a7586`](https://github.com/gonglei007/GGFramework-Demo/tree/e2a7586a1325fc8dd762b55d1105de81b9825154) | [GGNetwork `7e371ea`](https://github.com/gonglei007/GGFramework-GGNetwork/tree/7e371eab8b9de00f06e713ca7bd8468ebb890ea0) |
| HTTP 路径 | Demo `HttpNetworkSystem → TaskSystem → BestHTTP → ShowcaseServer` | 默认 UnityWebRequest，通过 HTTP 工厂适配底层；可选 BestHTTP 需安装插件及 `GGNETWORK_BESTHTTP` 宏；缺失时显式失败 |
| 反馈接口 | `onWaiting`、`onResponseError`、`onDialog` | `UIAdaptor` 与 `LogAdaptor`，不是 Demo 的同一套事件接口 |
| Core 依赖 | Demo 固定 `v0.3.0` | 固定提交的 manifest 为 `v0.1.1`；完整依据见导读源码基线 |
| 能验证的范围 | 本机真实 HTTP 请求、固定错误响应与交互恢复 | 本轮默认工程 162 项 EditMode 通过；真实后端联调另验 |

两套 API 不应混用，也不要把独立 GGNetwork 的源码直接覆盖到 Demo 后宣称原有验证仍然有效。独立模块的[快速接入](https://github.com/gonglei007/GGFramework-GGNetwork/blob/7e371eab8b9de00f06e713ca7bd8468ebb890ea0/documents/quickstart.md)和[手册](https://github.com/gonglei007/GGFramework-GGNetwork/blob/7e371eab8b9de00f06e713ca7bd8468ebb890ea0/documents/manual.md)用于理解接口；行为仍需与源码和运行结果核对。

## 复现步骤与预期

按导读的[统一复现入口](GGFramework.md#运行一次完整体验)固定 Demo 并完成准备，再进入 **Play Showcase → HTTP** 页。服务只监听 `127.0.0.1` 的系统分配端口，退出播放时关闭；以下请求不需要公网业务服务。

| 操作 | 预期结果 | 核对重点 |
|---|---|---|
| 点击“成功 200” | 收到 JSON，`NetworkCode` 为 200，等待状态结束 | 请求确实走 HTTP 后端，而非直接修改界面 |
| 点击“业务失败 409”，再关闭提示 | 显示业务拒绝反馈 | 测试服务返回 **HTTP 200 + JSON `code: 409`**；界面按钮的 409 不是 HTTP 状态码 |
| 点击“服务不可用 503” | HTTP 503，出现可重试反馈 | 区分服务错误与业务拒绝 |
| 在 503 提示中点击“取消 / 关闭”，等待并观察 | 提示关闭，等待状态结束，不因该决策主动重发 | 取消的是“是否重试”的决策，不证明此前请求未执行 |
| 再次触发 503，点击一次“重试” | 固定服务仍返回 503，再出现反馈；随后取消 | 这是再次访问固定失败服务，不是服务已经恢复；重试次数需用服务日志或抓包核对 |
| 最后点击“成功 200” | 正常收到 JSON，不残留上次错误提示 | 证明失败交互没有阻塞后续这个请求 |

“取消当前请求”调用当前请求的 `Abort`，与错误提示中的取消重试是两条路径。服务响应很快时，手点 Abort 未必能命中在途阶段；要验证在途取消与完成的竞争，需要额外的延迟服务及断言，不能用上表的取消重试代替。

## 对照源码理解职责

| 入口（固定提交） | 阅读什么 |
|---|---|
| [FrameworkShowcase.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.cs) | `SendRequest` 准入、回调、`ResolveNetworkDialog` 重试决策，以及退出时 Abort / 解除事件绑定 |
| [ShowcaseServer.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseServer.cs) | `/success`、`/business-error`、`/unavailable` 对应的 HTTP 状态与 JSON 内容，回环监听和关闭责任 |
| [ShowcaseSmoke.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSmoke.cs) | 200、业务 409、503、取消重试后空闲、后续恢复的断言 |
| [独立 HttpNetworkSystem.cs](https://github.com/gonglei007/GGFramework-GGNetwork/blob/7e371eab8b9de00f06e713ca7bd8468ebb890ea0/GGNetwork/Assets/Scripts/GGNetwork/Systems/HttpNetworkSystem.cs) | 默认后端选择、业务错误码开关、UI 适配与异常处理；不要仅凭枚举名判断重试安全性 |

Demo 的单请求等待状态便于观察流程，不能据此认定已有多请求隔离、全局背压或交易幂等。独立模块源码中的 `AutoRetry` 分支仍有避免立即无限重试的待办，错误路径可再次调用发送方法；未增加退避、总预算和出口并完成回归前，不将它作为生产自动重试方案。

## 方案取舍

| 选择 | 适用条件 | 代价与验证要求 |
|---|---|---|
| 显式确认后重试 | 玩家可以决定是否再次进行的操作，且业务允许安全重试 | 处理关闭、重复点击与过期决策；确认框本身不能防重复订单 |
| 自动退避重试 | 可重试错误，且查询或同业务 ID 操作具备明确安全契约 | 总截止时间、次数、抖动、取消与队列预算必须实现并测试；本篇 Demo 未证明这些能力 |
| 业务拒绝后结束 | 权限、库存、版本等需要业务处理的错误 | 依据契约展示反馈、查询权威状态或引导升级，不能把所有错误当作网络断开 |
| 原生 API / 现有客户端库 | 简单请求或团队已有成熟网络层 | 可保留原传输，只借鉴反馈与生命周期编排，比较新依赖与迁移成本 |
| 引入独立 GGNetwork | 需要其 HTTP、长连接、解析或反馈适配层，且能维护所选实现 | 分别验收后端、平台和业务协议；Demo 的 BestHTTP 通过不能替代 UnityWebRequest 验收 |

<a id="验证方法与结果分层"></a>

## 验证方法与证据边界

### 现有可复现验证

1. 按上表手工执行，记录操作顺序、状态、实际错误码和日志。手工重试的实际请求次数需要额外观察服务端日志或抓包。
2. 按[统一复现入口](GGFramework.md#运行一次完整体验)执行完整大厅冒烟，保留报告与日志；HTTP 只是其中一部分。
3. 对照 `ShowcaseSmoke.cs` 的实际断言。HTTP 部分检查成功、业务拒绝、503、取消重试后的空闲与后续恢复；没有自动验证“手工重试恰好新增一次请求”或取消后的服务端执行状态。
4. 需要验证旧连接、迟到响应、截止时间、请求关联与关闭竞争时，在 GameDevMind 根目录运行已有教学模型：

```bash
python -m unittest discover -s 'code/gamedevmind/3.研发能力/3.1.4.客户端网络系统/client_network' -p 'test_*.py' -v
```

该 [Python 生命周期模型](../../code/gamedevmind/3.研发能力/3.1.4.客户端网络系统/client_network/README.md)使用人工事件，不是 GGNetwork 的传输适配器，也没有与其绑定。模型通过不能证明框架实现具备相同保证。

本轮结果与未覆盖项见[运行记录](GGFrameworkUnity验证记录.md)；历史证据与 CI 的区别见导读的[证据分层](GGFramework.md#验证方法与证据边界)。

本轮修复独立 GGNetwork 默认检出对未安装 BestHTTP 的无条件编译依赖，162/162 包含 2 项缺失依赖回归。Demo 生命周期另验大厅销毁后的回环监听关闭；没有补上延迟 HTTP、Abort / 完成竞争或真实第三方后端联调。

### 接入项目后仍需验证

| 待验证问题 | 故障注入与验收要点 |
|---|---|
| 重试是否有界 | 真实后端持续超时 / 503，核对次数、退避、总耗时与停止出口 |
| 请求结果是否唯一交付 | 延迟、重复、乱序响应与 Abort / 完成竞争，核对业务回调和等待计数 |
| 页面或账号变化是否隔离 | 关闭页面、换账号后交付旧响应，不得更新新页面或新会话 |
| 传输恢复是否等于业务恢复 | 断网、切网、前后台与重认证，恢复订阅和权威状态后才允许相应业务 |
| 写操作是否安全 | 服务端提交后丢失响应，按同业务 ID 查询或安全重试；支付以服务端验单与幂等为准 |
| 域名与安全传输是否正确 | 目标平台 DNS / TLS / IPv6、代理与证书失败；不以 IP 替换或 HTTPDNS 代替身份校验 |
| 是否承受并发与慢消费者 | 请求数、在途字节、队列年龄、主线程派发和内存均有预算及过载出口 |

这些是待执行的项目测试，不是本篇 Demo 已有结论。

## 不适用场景

本篇不覆盖 WebGL 本机 TCP 服务、移动端真机弱网、独立 GGNetwork 的 HTTPDNS / WebSocket 服务端联调、真实支付、TLS 安全验收和生产容量。也不适用于取消后用新订单号自动重发、凭 UI 遮罩防重复交易，或把连接建立直接视为恢复可玩。

## 图谱知识点映射

- [客户端网络系统](../../mds/3.研发能力/3.1.4.客户端网络系统.md)：主循环交付、请求身份、取消、重试与关闭责任。
- [网络与通信](../../mds/2.技术能力/2.2.1.网络与通信.md)：协议、传输与服务身份。
- [支付与变现](../../mds/6.运营能力/6.3.2.帐号与支付.md)：未知结果、权威验单与幂等。

继续阅读：[GGFramework 实践导读](GGFramework.md) · [返回首页](../../README.md#可立即使用的资源)。
