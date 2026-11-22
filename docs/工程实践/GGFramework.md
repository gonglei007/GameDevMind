# 从知识点到 Unity 工程：GGFramework 实践导读

读过状态机、资源加载和客户端网络的原理后，可以通过一个能操作、能观察结果的工程，继续研究这些能力如何协作。本文按问题组织 GGFramework 的阅读与体验路径，先观察行为，再定位实现，最后判断是否适合自己的项目。

**项目关系：** GGFramework 是本知识库作者维护的项目系列。这里将其作为工程参考，展示实现与取舍；采用前仍需与项目已有方案比较。通用知识保留在图谱，跨模块架构以 [GGFramework-Docs](https://github.com/gonglei007/GGFramework-Docs) 为来源，各模块 API 和接入步骤以模块仓库为来源。

**复核日期：** 2026-11-20。本轮实际运行 Unity Demo、独立模块测试与 Windows x64 Mono Player，修复退出与依赖问题；[环境、逐项结果和未覆盖项](GGFrameworkUnity验证记录.md)单独归档，未完成生产接入验收。各类证据的范围见[验证方法与证据边界](#验证方法与证据边界)。

## 适用条件

| 你目前的任务 | 开始前需要具备什么 | 推荐读法 |
|---|---|---|
| 理解客户端系统如何协作 | C# 与 Unity 场景、组件、协程基础 | 先运行 Demo，再沿实际调用定位模块 |
| 为已有工程评估某项能力 | 明确目标平台、Unity 版本、依赖与现有接口 | 只评估对应模块，比较改造与维护成本 |
| 研究模块拆分与复用 | 了解程序集、UPM 与版本锁定 | 对照 Core、依赖矩阵和架构决策记录 |

六篇共用的 Demo 环境为 **Windows Editor / Windows x64 Mono Development Player、Unity 6000.3.13f1**，已在[本轮运行记录](GGFrameworkUnity验证记录.md)中实际执行；需要 Git，首次包解析需访问 GitHub 和 Unity 包服务。Core 稳定包声明最低 Unity 2021.3，这只是包声明，不能代替 Demo 的实际验收范围。其他平台、构建后端或 Unity 版本需单独验证；Lua 还需匹配平台的 ToLua 原生插件。

## 固定源码基线

| 核对对象 | 固定源码依据 | 依赖与边界 |
|---|---|---|
| 集成 Demo | [e2a7586 manifest](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Packages/manifest.json) | Core `v0.3.0`，已启用包测试；含本轮生命周期与 Prefab 修复，业务模块和 ToLua 使用内置源码 |
| Core 稳定包 | [c0567a8 package.json](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/package.json) | 已发布 `v0.3.0`，Demo 使用此提交 |
| Core 开发快照 | [7e0fa45 package.json](https://github.com/gonglei007/GGFramework-Core/blob/7e0fa45c3b514fde135d04f5449a2e0bc9202b4a/package.json) | `0.4.0-preview.1`；新增资源契约不在 Demo 稳定包范围内，由 Core 独立 CI 的 104 项测试另验 |
| 独立 GGResource | [14c7a68 manifest](https://github.com/gonglei007/GGFramework-GGResource/blob/14c7a685b2b75686e5585f852d1bab93f5f46195/GGResource/Packages/manifest.json) | Core `v0.1.1`；资源页只运行其特定集成路径 |
| 独立 GGNetwork | [7e371ea manifest](https://github.com/gonglei007/GGFramework-GGNetwork/blob/7e371eab8b9de00f06e713ca7bd8468ebb890ea0/GGNetwork/Packages/manifest.json) | Core `v0.1.1`；默认 UnityWebRequest；可选 BestHTTP 需安装插件并启用宏，Demo 使用其内置 BestHTTP |
| 独立 GGUI | [12ffe13 manifest](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Packages/manifest.json) | 默认分支 master，Core `v0.1.1`；独立后端与 Demo 旧副本分别评估 |
| 独立 GGUser | [2f9f5ad manifest](https://github.com/gonglei007/GGFramework-GGUser/blob/2f9f5ad9291300faff00c31d953c3218323bdc82/GGUser/Packages/manifest.json) | Core `v0.2.0`；传统接口、聚合平台与 ShowcaseSDK 分开验证 |

各篇在此基线上链接具体实现与测试。文中的“当前实现”指这些固定提交；采用更新版本时重新核对 manifest、API 和运行结果。ToLua 等第三方实现保留各自来源，不归为 Core 包能力。

## 从问题选择实践入口

| 想观察什么 | 图谱主入口（双向） | 工程中的观察任务 | 实践文档 |
|---|---|---|---|
| 状态、事件与对象复用 | [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md) | 状态守卫拒绝后重新进入；退订后发布事件；核对池复用与退出责任 | [Core 基础能力实践](GGFrameworkCore基础能力实践.md) |
| 资源来源与释放责任 | [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)、[产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md) | 加载两次、释放两次，观察引用计数；读取缺失资源后恢复；构建并加载本地 Bundle | [资源管理实践](GGFramework资源管理实践.md) |
| 请求失败后的交互与恢复 | [客户端网络系统](../../mds/3.研发能力/3.1.4.客户端网络系统.md) | 区分成功、业务拒绝和 HTTP 503；取消重试后再发成功请求 | [客户端网络实践](GGFramework客户端网络实践.md) |
| 页面与窗口的归属 | [UI系统](../../mds/3.研发能力/3.1.6.UI系统.md)、[客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md) | 背包 → 详情窗口 → 返回，观察页面栈、窗口归属与生命周期 | [UI 管理实践](GGFrameworkUI管理实践.md) |
| SDK 与游戏业务解耦 | [用户与帐号系统](../../mds/3.研发能力/3.3.5.用户与帐号系统.md)、[支付与变现](../../mds/6.运营能力/6.3.2.帐号与支付.md) | 注入登录失败再重试；区分支付事件、模拟验单与真实后端责任 | [用户与 SDK 接入实践](GGFramework用户与SDK接入实践.md) |
| Lua 规则与热更新边界 | [产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md)、[客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md) | 修改倍率并读取返回值；核对加载器、绑定与脚本释放责任 | [Lua 与热更新实践](GGFrameworkLua与热更新实践.md) |

上表维护六篇实践与十组双向图谱入口；各篇的其他知识链接用于延伸阅读。首页的 [GGFramework 工程实践区](../../README.md#ggframework-工程实践)展示六篇主题与运行记录，本页组织完整阅读路径。

## 运行一次完整体验

各篇的准备步骤统一在这里维护。先安装上述 Unity 版本和 Git，固定 Demo 提交：

```bash
git clone https://github.com/gonglei007/GGFramework-Demo.git
cd GGFramework-Demo
git checkout --detach e2a7586a1325fc8dd762b55d1105de81b9825154
```

1. 打开 `unity_project`，记录 Demo / Core 提交、Unity、平台和构建后端。
2. 等待 Package Manager 完成解析，核对 manifest 与包锁定记录。无需同级克隆其他模块；修改为本地包或更新依赖后需重新验证。
3. 在非播放状态执行 **GGFramework → Demo → Build Sample Bundles**，为真实本地 AssetBundle 体验和完整冒烟测试生成资源。它只生成示例配置的 Bundle；切换目标平台后重新构建。
4. 选择 **Play Showcase**。先体验 Core，再进入资源、HTTP、UI、用户和 Lua 页；每次只执行一个操作，对照状态与回调记录。
5. 退出 Play Mode 后执行 **Run Smoke Tests**，保存 `unity_project/Logs/showcase-smoke-results.txt` 与 Unity 日志。这是完整大厅冒烟，包含所有专题；Core EditMode 包测试在 Test Runner 中另行执行，Demo 已配置 `testables`。完整命令、Player 构建和测试入口见[固定版本操作指南](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/documents/showcase-guide.md)。

6. 执行 **Run Lifecycle Checks Twice Without Domain Reload**，检查两个完整播放 / 退出周期和同会话重开；保存逐轮报告。原始失败、修复依据及 Player 生命周期命令见[实跑记录](GGFrameworkUnity验证记录.md)。

需要每次修改后重复验证时，使用[自动化回归与 CI 复现](GGFramework自动化回归与CI.md)：六仓各自维护执行契约，统一脚本检查准确提交、退出码、新报告和关键清理断言；拥有者提交通过一次性 Windows runner 执行真实 Unity CI。

构建示例 Bundle 是完整冒烟的前置条件。单独体验 Core、HTTP、UI、SDK、Lua 页时不代表已经使用了 Bundle；资源页的 LocalResources、Simulation 与真实 Bundle 也分别验收。切换目标平台后重新构建 Bundle。

首次体验建议完成三个对照：取消订阅前后金币是否变化、资源引用是否归零、HTTP 失败后是否能恢复。每个对照都应能从界面状态追到对应 API，避免只看功能列表。

## 方案取舍

| 路径 | 适合什么情况 | 需要承担的代价 |
|---|---|---|
| 运行 Demo 研究集成 | 需要快速理解模块协作与故障反馈 | Core 来自固定 UPM 包，业务模块多为源码副本；不会自动获得所有独立模块的修复 |
| 只引入 Core | 需要其中的状态机、事件、对象池或调度能力 | 按 UPM 固定标签接入，核对命名空间、既有同名类与退出生命周期 |
| 单独评估 GGNetwork / GGResource / GGUI / GGUser | 现有系统在对应职责上有明确缺口 | 核对模块自己的版本、第三方依赖、协议及适配层；这些模块并非全部已做成独立 UPM 包 |
| 保留现有库或使用 Unity 原生 API | 需求简单，或团队已有成熟方案 | 自行组织业务生命周期与测试；可只参考 GGFramework 的设计，不迁移整套工程 |

各消费工程分别锁定 Core 版本，不能因 Demo 使用 `v0.3.0` 就把其他模块全部改成相同版本。当前依赖、源码副本和架构决策统一查阅[模块关系](https://github.com/gonglei007/GGFramework-Docs#模块关系)与 [ADR](https://github.com/gonglei007/GGFramework-Docs/tree/main/adr)。

## 不适用场景

- 需要直接上线的完整游戏客户端。各篇列出了尚需项目验证的契约，接入方必须验收自己的目标环境。
- 希望通过 Demo 证明独立 GGNetwork 的全部能力。Demo 的 HTTP 链路使用 BestHTTP 副本，独立模块默认使用 UnityWebRequest，详见[网络实践的实现对照](GGFramework客户端网络实践.md#两条实现路径)。
- 需要直接在 WebGL 复现回环 HTTP 服务。示例服务使用本机 TCP；其他桌面平台也需匹配的 ToLua 原生插件。
- 希望 GGUI 的现有 UGUI 后端直接替代 NGUI。独立 GGUI 默认 NGUI，UGUI 已有部分控件实现，输入环境、布局与动画等仍待补齐；Demo 的 IMGUI 面板不能证明该后端完整可用。
- 需要真实渠道支付、服务端验单或生产热更新验收。模拟 SDK 只产生本地事件，本地 Bundle 示例未覆盖完整发布、下载、校验和回滚链路。

<a id="验证方法与证据"></a>

## 验证方法与证据边界

| 证据层次 | 应检查什么 | 可以说明什么 |
|---|---|---|
| 固定源码核对 | 比较实际调用、默认参数、失败分支与测试断言 | 说明该提交的实现与覆盖意图；不等于已执行测试 |
| 文中的操作预期 | 按专题表格手工复现，保存实际结果 | 表格给出验收任务；未附运行报告的步骤不记为本轮通过 |
| 上游历史运行记录 | [2026-11-19 验收记录](https://github.com/gonglei007/GGFramework-Demo/blob/3039f9aad1813b8ad72e373a30b3eb073e0ee2eb/documents/showcase-verification.md) | Windows 11 / Unity 6000.3.13f1 / x64 Mono Development Player 的历史结果；原始报告未入库；与本轮独立保存的运行证据分开 |
| 本轮 Unity 实跑 | [2026-11-20 环境与结果](GGFrameworkUnity验证记录.md)，含脱敏断言、NUnit 逐项结果、原始摘要及失败前后对照 | 验证固定 Windows Editor / Mono Player 中所列 API 与退出路径；不证明全部内存无泄漏、所有竞态或生产服务可用 |
| 各仓自动化 Unity CI | [六仓回归工作流与复现](GGFramework自动化回归与CI.md)，逐一核对 PR / 合并提交、执行契约及保全的 artifact 结果 | 证明固定提交在所记环境下完成自动化测试；稳定 Core 与预览包分别计数，仍不覆盖真实渠道或补丁服务 |
| 本知识库文档 CI | 链接、导航与统计一致性，GitHub 桌面 / 手机展示，六篇实践及十组图谱双向跳转 | 证明系列可读、入口可达 |
| 本仓库教学模型 | 例如 Python 客户端网络生命周期模型；由各自 CI 检查 | 模型契约独立成立，不是 GGNetwork 适配器，也不证明框架拥有同一保证 |
| 读者本机复现 | 固定提交，执行指南中的测试，保存退出码、报告、日志与截图 | 证明所记录环境下的实际结果；独立模块的测试需在其工程中另跑 |
| 项目接入验收 | 真实后端、弱网、切网、前后台、场景关闭、业务幂等、容量与依赖升级 | 决定是否满足产品需求，必须由项目单独完成 |

历史记录中的稳定版 Core EditMode 为 66 / 66，大厅 Editor 冒烟为 28 / 28，Windows Player 冒烟为 27 / 27（不含 Editor Simulation）。这些数值描述历史记录。本轮另外重跑得到相同的 Core / 冒烟数量，并新增生命周期与独立模块实跑；详见[本轮结果](GGFrameworkUnity验证记录.md)。两者均不覆盖 Core 预览版或各独立模块全部路径。

其后接入的[独立 Unity CI](GGFramework自动化回归与CI.md)分别执行稳定包、Core 预览包及各模块契约；预览包 104 项不计为 Demo 稳定包 66 项的同一次验证，也不构成预览能力的生产验收。

建议记录 `提交 SHA / 包锁定版本 / Unity / 平台与构建后端 / 配置与来源 / 操作 / 预期 / 实际 / 日志位置 / 未覆盖项`，并标注结果属于源码核对、操作预期、历史运行、本轮文档验证还是项目验收。

## 来源与维护

本页的接入体验和边界以 [Demo 固定提交的操作指南](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/documents/showcase-guide.md)为复核基线；模块关系参考 [Docs 固定提交](https://github.com/gonglei007/GGFramework-Docs/blob/4bb2c05173424eca8a3bcc193a4ac6a43b332a84/README.md)。实际采用更新版本时，重新核对模块说明、manifest 与测试结果。

本文维护阅读路径和知识映射，不复制模块 API 手册；发现框架问题在对应模块反馈，发现本导读的链接、归类或验证表述问题在 GameDevMind 反馈。

继续阅读：[全部代码示例](../../code/README.md) · [返回首页](../../README.md#ggframework-工程实践)。
