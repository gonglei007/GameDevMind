# GGFramework 用户与 SDK 接入实践：登录状态与支付验证边界

本篇从“初始化完成后能做什么、谁确认登录有效、支付回调能否发货”出发，用 Demo 观察事件，再对照 GGUser 的传统 SDK 接口与聚合平台实现。身份建模见[用户与帐号系统](../../mds/3.研发能力/3.3.5.用户与帐号系统.md)，订单与发货见[支付与变现](../../mds/6.运营能力/6.3.2.帐号与支付.md)。

**项目关系与复核：** GGFramework 由本知识库作者维护；本文是工程参考。2026-11-20 完成固定源码核对与 Unity 实跑，实际结果及未覆盖项见[本轮运行记录](GGFrameworkUnity验证记录.md)。共用的[适用环境](GGFramework.md#适用条件)、[源码基线](GGFramework.md#固定源码基线)和[证据分层](GGFramework.md#验证方法与证据边界)由导读统一维护。

## 适用条件

- 具备 C#、Unity 组件、状态机与异步回调基础，需要隔离渠道 SDK 与游戏业务，或梳理已有登录、支付接入的责任。
- 真正上线需要渠道开发者配置、匹配的原生插件、可信游戏后端与订单服务；本地事件和模拟网关只用于研究调用流程。

## 三条路径与版本边界

| 核对对象 | 已有实现 | 不能混用的边界 |
|---|---|---|
| 独立 GGUser 的传统接口 | [2f9f5ad](https://github.com/gonglei007/GGFramework-GGUser/tree/2f9f5ad9291300faff00c31d953c3218323bdc82)，固定 Core `v0.2.0`；`GGFramework.GGUser` 命名空间，`UserSystem / ISDK / UserManager` | UserSystem 使用 Core 状态机；SDK 登录成功不表示游戏服认证完成 |
| 同一独立模块的聚合平台 | `GGPlatform`、`ILoginChannel / IPayChannel`、可注入网关传输 | 默认只注册 simulation；`PayRequest / PurchaseResult` 不是传统 `Order`，也没有自动同步传统 UserSystem 的会话 |
| 集成 Demo | [e2a7586](https://github.com/gonglei007/GGFramework-Demo/tree/e2a7586a1325fc8dd762b55d1105de81b9825154)，固定 Core `v0.3.0`；旧 UserSystem 副本与显式注入的 `ShowcaseSDK` | 仍使用旧状态机与全局类型，订单为 `UserSystem.Order`；没有运行聚合平台或真实商店支付 |

独立模块另有一个 [UGUI Demo](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Demo/Scripts/Demo.cs)：它运行聚合平台，却用本地 `onPost` 委托直接返回固定平台凭证和 `delivered: true`。日志显示 POST 不代表真的发出了网络请求；不要与集成体验大厅混为同一条验证链路。

## 初始化：配置、SDK 就绪与业务就绪分开

传统接口依据 [UserSystem.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/Systems/UserSystem.cs)：

| 操作 | 实际行为 | 接入责任 |
|---|---|---|
| 获取 UserSystem | Awake 建立状态机，并默认创建 NativeSDK | 记录实例与订阅的拥有者，不把实例存在当成 SDK 已就绪 |
| `ConfigureSDK(implementation)` | 拒绝 null，要求状态仍为 None；更换默认 NativeSDK 时退订它的静态桥接处理器 | 在第一次 Login 前注入；这个状态检查不是取消在途请求或运行中热切换协议 |
| 独立模块 `Init(channel)` | 清 `readyLogin` 并保存 channel；不调用 SDK.Init，不重置整个会话 | Demo 副本只有 `Init()`，不要跨版本照抄签名 |
| `Login()` | 从 None 调度进入 SDKIniting，再由初始化成功推进 SDK 登录；部分中间状态会再次调用初始化或登录 | 状态迁移经协程调度，按钮需防重复；不要假定同步完成或默认只发一次请求 |
| `SDKInitSuccess` 事件 | 先广播，若已有登录意图再调度 SDKLogining；不保证经过 SDKInited | 分别观察事件和状态，初始化成功不等于已登录或可发货 |

聚合平台则应先调用 `GGPlatform.Init(config)`，再注册真实渠道并设置 `Gateway.onPost`，最后发起业务。Init 会重建 Registry、Gateway 和 Router，重复初始化会丢失先前注册与传输注入。Registry 首次取渠道时才创建实例并调用其 `Init()`；该接口没有异步初始化完成回调，真实适配器需要自己处理“尚未就绪”的请求。

## 登录状态：本地状态不是服务端认证结果

- 传统 `CallSDKLoginSuccess(User)` 保存用户，再调度进入 SDKLogined；`HasLogined()` 只检查这个状态。失败回调主要广播事件，没有完整的回滚、超时、重试预算或旧请求代次隔离。
- [UserManager.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/User/UserManager.cs)的 `Authing_Enter / Logining_Enter` 仍把游戏服认证与登录留为 TODO，直接推进到 Logined，登录响应可能未赋值。它的 `HasLogined()` 不能证明服务端已认可渠道凭证。
- `CallSDKLogoutSuccess` 先清 UserInfo、广播，再调度 SDKInited；事件发生时状态可能尚未迁移。UserManager 的登出处理也没有同步复位其状态机。业务需要统一清理会话、角色与在途请求，避免旧帐号结果写入新帐号。
- 聚合平台的 Login 是“渠道登录 → Gateway.ExchangeToken”。[GGGatewayClient.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/Platform/GGGatewayClient.cs)未注入传输时会拼出模拟平台 token；注入后若响应为空、缺字段或解析失败，也可能保留原渠道结果的 `success = true`。接入方需为认证响应增加明确的拒绝路径，不能只检查这个布尔值。
- 聚合 Logout 只转交渠道，没有替业务统一维护权威会话；NativeSDK 在 Editor 的 Logout / Quit 也没有执行退出流程。Demo 模拟器的成功登出不能外推到这些路径。

建议项目明确“渠道凭证取得、服务端认证成功、区服登录完成、会话失效”四个时点，以后端签发且验证有效的平台会话驱动受保护业务。服务端拒绝、token 过期、登出后迟到回调、切换帐号和断线恢复都应有独立验收；这些不是当前框架已提供的完整契约。

## 渠道适配：接口存在不等于平台已接通

| 路径 | 源码状态 | 选择时需核对 |
|---|---|---|
| 传统 `ISDK` | Init、Login、Logout、Quit、Pay、SubmitData 六类操作；可通过 ConfigureSDK 注入 | 自行规范结果结构、线程切回、重复 / 迟到回调和退出时退订 |
| `SDKFactory` | NativeSDK、ZhiShangSDK 有创建分支；QuickSDK 在 `QUICK_SDK` 宏下创建，未启用时返回 null | 宏、原生库、包名、签名、权限与渠道配置；工厂能创建不代表真机验收通过 |
| NativeSDK | Editor 下使用模拟分支；移动端调用原生桥接 | 登录解析 `accountid / token`；仍需后端校验。原生 LogoutSuccess 分支调用 Application.Quit，不是清用户的 CallSDKLogoutSuccess |
| 聚合 `IChannel` 及登录 / 支付子接口 | 默认 SimulationChannel；宿主通过 RegisterChannel 提供其他实现 | 没有随默认注册得到 Apple / Google 商店接入；商品映射、商店连接、凭证与结束事务语义需逐渠道实现 |
| Demo 的 ShowcaseSDK | 显式注入，提供失败一次、三种支付结果和本地 UID 文件 | 不经生产 SDKFactory 选择；仅用来观察客户端业务事件 |

依据见 [ISDK.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/User/ISDK.cs)、[SDKFactory.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/User/SDKFactory.cs)、[NativeSDK.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/User/NativeSDK/NativeSDK.cs)与 [ChannelInterfaces.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/Channels/ChannelInterfaces.cs)。NativeSDK 和独立模块 Demo 还有完整回调 / 请求内容日志，生产接入应先去除 token、票据等敏感字段。

## 支付回调与服务端验单

### 传统接口只交付客户端事件

`SDKPay` 委托给 ISDK，成功、失败与取消回调只广播事件，没有验单和发货服务。UserSystem 未统一强制登录门禁；ShowcaseSDK 的“未登录拒绝支付”是该模拟器自己的检查。

Demo 使用订单 `demo-order`、商品 `demo-coins`、金额 0，回调传入本地订单 id。NativeSDK 的 PaySuccess 则传空字符串，失败 / 取消读取源码中的 `customorgerid` 字段。不能把所有事件参数当成统一的渠道流水或收据，也不能收到 SDKPaySuccess 就增加服务端余额。

### 聚合接口组织流程，真实验单由后端承担

[GGPlatform.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/Platform/GGPlatform.cs)当前路径是“候选路由 → Connect → QueryProducts → Purchase → Gateway.Verify → 处理结果”：

| 分支 | 当前行为 | 业务解释 |
|---|---|---|
| 连接失败或商品不可用 | 尝试下一个候选渠道 | 回退发生在购买之前；不能推断为所有失败都自动换渠道 |
| 已发起 Purchase 后 | 失败、挂起或验单未通过均不再回退购买 | 不应因回调超时就新建订单重复扣款，先查询原交易状态 |
| Pending | 返回 `success = false`，不 Verify、不 Finish | 挂起不是确定失败，也不是可发货状态 |
| 非 Purchased 的其他结果 | 调用 FinishTransaction 后返回失败 | 这是现有分支；不能把“只有发货后才 Finish”当成整个函数所有路径的行为 |
| Purchased 且 `verify.delivered` 为 true | FinishTransaction，再返回成功 | 当前仅信任网关响应；后端必须先完成可信校验与幂等发货 |
| Purchased 但验单未通过 | 不 Finish，记录失败并返回 | 应保留并查询 / 补偿，不能凭客户端失败提示认定从未扣款 |

`Gateway.onPost` 为空时，Verify 直接把 Purchased 判为模拟发货成功。即使注入了委托，也要核对它是否真的连接可信后端；独立模块 Demo 的委托仍然直接返回通过。框架没有提供可据此上线的订单数据库、渠道验单服务或发货账本。

真实后端应绑定已认证用户、渠道、商品与业务订单，核对渠道凭证和交易状态，以渠道适用的交易身份防重放，并让发货与去重记录可靠提交。Google Play 应把 purchaseToken 送到安全后端校验，只对 PURCHASED 发货，不能把可能缺失的 orderId 一概当成去重主键；确认与消耗还需区分商品类型，见 [Google Play 安全指引](https://developer.android.com/google/play/billing/security)。Apple 新接入应按 [App Store Server API](https://developer.apple.com/documentation/appstoreserverapi)与签名交易数据的验证流程设计；旧 verifyReceipt 接口已弃用，见 [Apple 收据验证说明](https://developer.apple.com/documentation/storekit/validating-receipts-with-the-app-store)。

### 补单、恢复与结束事务的范围

`ProcessUnfinished` 查询渠道未完成列表，只把 Purchased 送入同一验单流程；`onAllDone` 表示本轮处理结束，不表示每笔已发货。Restore 只是转交渠道恢复结果，不会自动执行验单发货。默认 [SimulationChannel](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Scripts/GGUser/Channels/Impl/SimulationChannel.cs)返回空的未完成 / 恢复列表，不能证明跨进程掉单恢复已经可用。

`FinishTransaction` 是适配接口，不能统一解释为“验单”或“消耗所有商品”。真实适配器需按平台和商品类型落实 finish、acknowledge 或 consume，并处理发货后结束事务失败、重复通知、退款与订阅变化。订单对账、补偿和最终权益以服务端记录为准。

## 用集成 Demo 复现用户页

按导读的[统一复现入口](GGFramework.md#运行一次完整体验)固定 Demo 并完成准备，再进入 **Play Showcase → 用户** 页。按钮只驱动本地 ShowcaseSDK，不访问真实支付服务。

| 操作 | 预期与观察点 |
|---|---|
| 未登录时点击“注入一次登录失败” | 出现 SDKLoginFailed，保持未登录；记录事件与状态的顺序 |
| 再点击“登录” | 进入已登录，出现 SDKLoginSuccess；这只是 ShowcaseSDK 的本地结果 |
| 分别点击“支付成功 / 支付失败 / 支付取消” | 各自得到对应事件；记录订单 id 和事件数，不应触发真实扣费 |
| 点击“登出”，再登录 | 先清用户并退出登录，再次登录 UID 不变；不代表 NativeSDK 的退出行为相同 |
| 退出并重新运行大厅 | 人工核对 UID 文件仍在时的稳定性；删除文件、卸载和换设备的身份恢复需另验 |

调用顺序可在 [FrameworkShowcase.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.cs)和 [ShowcaseSDK.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSDK.cs)核对：先获取 UserSystem，构造并注入模拟器，订阅事件，再调用无参数 Init。模拟 UID 保存在 `Application.persistentDataPath/GGFrameworkShowcase/demo-uid.txt`；`demo-token` 是固定演示字符串，不是经过认证的会话。

## 方案取舍与不适用场景

| 选择 | 适用条件 | 代价与限制 |
|---|---|---|
| 传统 ISDK 适配 | 已有单一渠道或历史 UserSystem 业务，需要隔离 SDK 调用 | 自行补齐认证、状态一致性、并发 / 退出契约与订单服务 |
| 聚合平台接口 | 需要研究多渠道路由、商品查询、验单后结束事务和补单分工 | 真实适配器、异步就绪、可信传输与严格认证响应仍需实现 |
| 先用 ShowcaseSDK | 先验收按钮、错误提示和客户端事件处理 | 不覆盖独立聚合平台，更不覆盖真实商店与服务端 |
| 保留已有成熟接入 | 已有可信会话、支付与对账体系 | 可仅参考接口和责任划分，比较迁移成本与平台维护负担 |

不适用于把任一本地 HasLogined 当成认证证明，把支付成功事件当成发货凭证，或把模拟网关、空恢复列表和单次冒烟通过当成上线验收。跨平台帐号绑定、游客迁移、多端会话、订阅续期、退款与财务对账也需要独立方案。

## 验证方法与证据边界

| 已有证据 | 覆盖范围 | 未证明什么 |
|---|---|---|
| [SDKInjectionTests.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Tests/EditMode/SDKInjectionTests.cs) | 注入、null 拒绝、初始化事件、注入取消不再附加 Editor 成功回调 | 真实渠道、多线程或所有请求全局恰好一次 |
| [GGPlatformEditModeTests.cs](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Assets/Tests/EditMode/GGPlatformEditModeTests.cs) | 假渠道 / 网关下的路由回退、Pending、验单后 Finish、验单拒绝保留、未完成列表和恢复委托 | 真实网络认证、商店票据、持久化账本或真机恢复 |
| [ShowcaseSmoke.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSmoke.cs) | 登录失败后成功，三种支付事件，成功支付事件数增加一次，登出后再登录 UID 一致 | 所有回调唯一、跨进程持久化、NativeSDK 或聚合平台通过 |

本轮结果与未覆盖项见[运行记录](GGFrameworkUnity验证记录.md)；历史证据与 CI 的区别见导读的[证据分层](GGFramework.md#验证方法与证据边界)。本轮已分别运行独立 GGUser EditMode 71/71 与 PlayMode 11/11；使用假渠道和网关，没有接入真实渠道、认证或支付服务。

| 接入待验项 | 注入方式与通过条件 |
|---|---|
| 初始化与登录竞争 | 双击、初始化延迟 / 失败、超时重试；记录请求代次与事件，旧结果不覆盖新意图 |
| 可信认证与退出 | 后端拒绝、空 / 非法响应、token 失效、登出后迟到回调、切换帐号；确认受保护接口拒绝无效会话 |
| 真机渠道 | 使用渠道沙箱分别验证目标平台、原生桥接、前后台和进程重启，不以 Editor 模拟代替 |
| 交易状态与幂等 | Pending、取消、重复 / 乱序通知、伪造票据、错用户 / 商品、验单超时；后端只对合法交易发一次权益 |
| 掉单与结束事务 | 分别在购买后、发货后和 Finish 前后断网 / 杀进程；重启查询恢复，不重复扣费或发货 |
| 恢复、退款与对账 | 以真实沙箱非消耗品 / 订阅验证恢复与变更；核对渠道流水、业务订单、发货账本及退款结果 |

保存 `GGUser / Demo SHA、Core、Unity、平台与后端、渠道 SDK 版本、脱敏订单标识、操作序列、实际回调 / 状态、服务端发货记录与未覆盖项`。验收依据应能区分客户端观察与服务端事实。

继续阅读：[GGFramework 实践导读](GGFramework.md) · [用户与帐号系统](../../mds/3.研发能力/3.3.5.用户与帐号系统.md) · [支付与变现](../../mds/6.运营能力/6.3.2.帐号与支付.md) · [支付掉单与重复发货](../../cases/payment-duplicate-delivery.md) · [返回首页](../../README.md#可立即使用的资源)。
