# 从知识点到 Unity 工程：GGFramework 实践导读

读过状态机、资源加载和客户端网络的原理后，可以通过一个能操作、能观察结果的工程，继续研究这些能力如何协作。本文按问题组织 GGFramework 的阅读与体验路径，先观察行为，再定位实现，最后判断是否适合自己的项目。

**项目关系：** GGFramework 是本知识库作者维护的项目系列。这里将其作为工程参考，展示实现与取舍；采用前仍需与项目已有方案比较。通用知识保留在图谱，跨模块架构以 [GGFramework-Docs](https://github.com/gonglei007/GGFramework-Docs) 为来源，各模块 API 和接入步骤以模块仓库为来源。

**复核日期：** 2026-11-20。本轮核对公开文档与源码，未重新运行 Unity 工程；上游已记录的运行结果与本知识库 CI 的验证范围分别见[验证方法与证据](#验证方法与证据)。

## 适用条件

| 你目前的任务 | 开始前需要具备什么 | 推荐读法 |
|---|---|---|
| 理解客户端系统如何协作 | C# 与 Unity 场景、组件、协程基础 | 先运行 Demo，再沿实际调用定位模块 |
| 为已有工程评估某项能力 | 明确目标平台、Unity 版本、依赖与现有接口 | 只评估对应模块，比较改造与维护成本 |
| 研究模块拆分与复用 | 了解程序集、UPM 与版本锁定 | 对照 Core、依赖矩阵和架构决策记录 |

整体体验路径按 **Windows Editor / Windows 桌面 Player、Unity 6000.3.13f1** 编写；需要 Git，并在首次包解析时访问 GitHub 与 Unity 包服务。Core 声明最低 Unity 2021.3，与整个 Demo 的验证版本是两个范围，不能相互替代。其他平台、IL2CPP 或其他 Unity 版本需要另行编译和运行验证。

## 从问题选择实践入口

| 想观察什么 | 图谱中的原理入口 | 工程中的观察任务 | 实现入口 |
|---|---|---|---|
| 状态、事件与对象复用 | [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md) | 状态守卫拒绝后重新进入；取消订阅后发布事件；取出并归还池对象 | [Core](https://github.com/gonglei007/GGFramework-Core) |
| 资源来源与释放责任 | [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)、[产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md) | 加载两次、释放两次，观察引用计数；读取缺失资源后恢复；构建并加载本地 Bundle | [资源管理实践](GGFramework资源管理实践.md) |
| 请求失败后的交互与恢复 | [客户端网络系统](../../mds/3.研发能力/3.1.4.客户端网络系统.md) | 区分成功、业务拒绝和 HTTP 503；取消重试后再发成功请求 | [客户端网络实践样板](GGFramework客户端网络实践.md) |
| 页面与窗口的归属 | [UI系统](../../mds/3.研发能力/3.1.6.UI系统.md) | 背包 → 详情窗口 → 返回，观察页面栈、窗口归属与生命周期 | [UI 管理实践](GGFrameworkUI管理实践.md) |
| SDK 与游戏业务解耦 | [用户与帐号系统](../../mds/3.研发能力/3.3.5.用户与帐号系统.md)、[支付与变现](../../mds/6.运营能力/6.3.2.帐号与支付.md) | 注入登录失败再重试；区分支付事件、模拟验单与真实后端责任 | [用户与 SDK 接入实践](GGFramework用户与SDK接入实践.md) |

## 运行一次完整体验

1. 安装上述 Unity 版本和 Git，克隆 [GGFramework-Demo](https://github.com/gonglei007/GGFramework-Demo)，打开其中的 `unity_project`。记录 Demo 提交 SHA、Unity 版本、平台和构建后端。
2. 等待 Package Manager 完成解析。当前 Demo 固定引用已发布的 Core `v0.3.0`；无需同级克隆其他模块，首次导入仍需要网络。
3. 在非播放状态执行 **GGFramework → Demo → Build Sample Bundles**，为真实本地 AssetBundle 体验和完整冒烟测试生成资源。它只生成示例配置的 Bundle；切换目标平台后重新构建。
4. 选择 **Play Showcase**。先体验 Core，再进入资源、HTTP、UI 和用户页；每次只执行一个操作，对照状态与回调记录。
5. 退出 Play Mode 后执行 **Run Smoke Tests**，保存 `unity_project/Logs/showcase-smoke-results.txt` 与 Unity 日志。完整命令、Player 构建和测试入口见[开发者体验指南](https://github.com/gonglei007/GGFramework-Demo/blob/main/documents/showcase-guide.md)。

首次体验建议完成三个对照：取消订阅前后金币是否变化、资源引用是否归零、HTTP 失败后是否能恢复。每个对照都应能从界面状态追到对应 API，避免只看功能列表。

## 方案取舍

| 路径 | 适合什么情况 | 需要承担的代价 |
|---|---|---|
| 运行 Demo 研究集成 | 需要快速理解模块协作与故障反馈 | Demo 使用自己的模块源码副本，不会自动获得独立模块的修复 |
| 只引入 Core | 需要其中的状态机、事件、对象池或调度能力 | 按 UPM 固定标签接入，核对命名空间、既有同名类与退出生命周期 |
| 单独评估 GGNetwork / GGResource / GGUI / GGUser | 现有系统在对应职责上有明确缺口 | 核对模块自己的版本、第三方依赖、协议及适配层；这些模块并非全部已做成独立 UPM 包 |
| 保留现有库或使用 Unity 原生 API | 需求简单，或团队已有成熟方案 | 自行组织业务生命周期与测试；可只参考 GGFramework 的设计，不迁移整套工程 |

各消费工程分别锁定 Core 版本，不能因 Demo 使用 `v0.3.0` 就把其他模块全部改成相同版本。当前依赖、源码副本和架构决策统一查阅[模块关系](https://github.com/gonglei007/GGFramework-Docs#模块关系)与 [ADR](https://github.com/gonglei007/GGFramework-Docs/tree/main/adr)。

## 不适用场景

- 需要未经评估直接上线的完整游戏客户端。多个业务模块仍标注内测状态，接入方必须验收自己的目标环境。
- 希望通过 Demo 证明独立 GGNetwork 的全部能力。Demo 的 HTTP 链路使用 BestHTTP 副本，独立模块默认使用 UnityWebRequest，详见[网络实践的实现对照](GGFramework客户端网络实践.md#两条实现路径)。
- 需要直接在 WebGL 复现回环 HTTP 服务。示例服务使用本机 TCP；其他桌面平台也需匹配的 ToLua 原生插件。
- 希望 GGUI 的现有 UGUI 后端直接替代 NGUI。独立 GGUI 当前默认 NGUI，UGUI 为待补全的占位实现；Demo 大厅的 IMGUI 操作面板也不能证明 UGUI 后端已实现。
- 需要真实渠道支付、服务端验单或生产热更新验收。模拟 SDK 只产生本地事件，本地 Bundle 示例未覆盖完整发布、下载、校验和回滚链路。

## 验证方法与证据

| 证据层次 | 应检查什么 | 可以说明什么 |
|---|---|---|
| 本知识库的文档与 CI | 链接、导航与统计一致性，GitHub 实际展示；已有 Python 生命周期模型 | 阅读路径可达、文档可读、教学模型契约成立；不证明 Unity 集成通过 |
| 上游维护者的运行记录 | [2026-11-19 验收记录](https://github.com/gonglei007/GGFramework-Demo/blob/3039f9aad1813b8ad72e373a30b3eb073e0ee2eb/documents/showcase-verification.md) | 记录了特定 Windows / Unity 环境中的编译、Core 测试与 Demo 冒烟；原始报告未入库，本轮未独立重跑 |
| 读者本机复现 | 固定提交，执行指南中的测试，保存退出码、报告、日志与截图 | 证明该提交在记录环境下的实际结果，不能跨平台外推 |
| 项目接入验收 | 真实后端、弱网、切网、前后台、场景关闭、业务幂等、容量与依赖升级 | 决定是否满足产品需求，必须由项目单独完成 |

建议保存一份自己的记录：`提交 SHA / Core 锁定版本 / Unity / 平台与后端 / 操作 / 预期 / 实际 / 日志位置 / 未覆盖项`。先完成一个任务的复现，再扩大接入范围。

## 来源与维护

本页的接入体验和边界以 [Demo 固定提交的操作指南](https://github.com/gonglei007/GGFramework-Demo/blob/3039f9aad1813b8ad72e373a30b3eb073e0ee2eb/documents/showcase-guide.md)为复核基线；模块关系参考 [Docs 固定提交](https://github.com/gonglei007/GGFramework-Docs/blob/4bb2c05173424eca8a3bcc193a4ac6a43b332a84/README.md)。实际采用更新版本时，重新核对模块说明、manifest 与测试结果。

本文维护阅读路径和知识映射，不复制模块 API 手册；发现框架问题在对应模块反馈，发现本导读的链接、归类或验证表述问题在 GameDevMind 反馈。

继续阅读：[用户与 SDK 接入实践](GGFramework用户与SDK接入实践.md) · [UI 管理实践](GGFrameworkUI管理实践.md) · [资源管理实践](GGFramework资源管理实践.md) · [客户端网络实践样板](GGFramework客户端网络实践.md) · [全部代码示例](../../code/README.md) · [返回首页](../../README.md#可立即使用的资源)。
