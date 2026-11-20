# GGFramework UI 管理实践：页面栈、窗口归属与生命周期

本篇从“返回时回到哪一页、窗口属于谁、隐藏后还剩下什么”出发，先用 Demo 观察页面与窗口状态，再对照独立 GGUI 的实际实现。UI 设计原理见 [UI系统](../../mds/3.研发能力/3.1.6.UI系统.md)，资产与引用计数见[资源管理实践](GGFramework资源管理实践.md)。

**项目关系与复核：** GGFramework 由本知识库作者维护；本文是工程参考。2026-11-20 完成固定源码核对与 Unity 实跑，实际结果及未覆盖项见[本轮运行记录](GGFrameworkUnity验证记录.md)。共用的[适用环境](GGFramework.md#适用条件)、[源码基线](GGFramework.md#固定源码基线)和[证据分层](GGFramework.md#验证方法与证据边界)由导读统一维护。

## 适用条件

- 具备 C#、Unity GameObject / 组件、Prefab 和事件回调基础，需要组织全屏页面、附属窗口与界面退出流程。
- 能为所选 UI 后端准备输入环境、Prefab、分层与资源约定。
- 先观察现有框架行为，再评估是否适合项目的 UI 后端、路由与资源契约；不将 IMGUI 演示面板当成目标平台完整 UI 验收。

| 核对对象 | 固定版本 | 与本篇相关的区别 |
|---|---|---|
| 独立 GGUI | [12ffe13](https://github.com/gonglei007/GGFramework-GGUI/tree/12ffe13297c281cbfa6253ac443aab1552ce3857)，默认分支 **master**，工程固定 Core `v0.1.1` | `GGFramework.GGUI` 命名空间，通过 `IUIImplementation` 适配后端 |
| 集成 Demo | [e2a7586](https://github.com/gonglei007/GGFramework-Demo/tree/e2a7586a1325fc8dd762b55d1105de81b9825154)，固定 Core `v0.3.0` | 使用旧 UI 源码副本，直接依赖 NGUI；体验大厅通过代码创建简单 UI 对象 |

Demo 的行为不能证明独立 GGUI 的接口层、资源异步创建或动画修复已被同一测试覆盖。独立模块的准备顺序与 Prefab 约定见[固定版本接入指南](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/documents/quickstart.md)。

## NGUI、UGUI 与 Demo 的支持状态

| 路径 | 已有实现 | 仍需补齐或验证 |
|---|---|---|
| 独立 GGUI 默认 NGUI | `UIPanel` 分层、NGUI 文本 / 按钮 / 进度 / 网格包装、补间与点击适配 | 实际 Prefab 绑定、输入穿透、目标平台、动画与资源生命周期仍需运行验证 |
| 独立 GGUI 的 UGUI | 创建 Canvas / GraphicRaycaster 分组；包装 `Text`、`Button`、`Slider`；支持按钮点击委托 | Init 中 EventSystem、根 Canvas / CanvasScaler 待完善；补间、布局重建、非 Button 遮罩点击仍有占位逻辑。不是可直接替换 NGUI 的完整后端 |
| Demo 体验大厅 | IMGUI 侧栏、按钮和状态框驱动旧 `UISystem / UIPage / UIWindow`，底层保留 NGUI 分组 | 未验证独立 UGUI 实现；状态框可显示不代表整套 NGUI Prefab、布局、射线或转场已验收 |

具体依据是 [NGUIImplementation.cs](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Scripts/GGUI/Implementation/NGUI/NGUIImplementation.cs)、[UGUIImplementation.cs](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Scripts/GGUI/Implementation/UGUI/UGUIImplementation.cs) 和 [UGUIControls.cs](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Scripts/GGUI/Implementation/UGUI/UGUIControls.cs)。例如 UGUI 的布局 `cellWidth` 目前只是字段，`Reposition` 和补间 `Play` 仍记录未实现警告；不能只看接口存在就认定功能完成。

独立 `UISystem` 在 Awake 中选择实现。需要自定义后端时，应在实例创建前调用 `SetImplementation`；实例已经初始化后再设置，并不会把已创建的控件自动迁移。切换后端也不等于已经可以删除工程内的全部 NGUI 依赖。

## 页面栈：入栈、隐藏与返回是不同操作

以下行为在两套 [独立 UISystem](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Scripts/GGUI/Systems/UISystem.cs)和 [Demo UISystem](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/Scripts/Systems/UISystem.cs)中均可核对：

| 调用 | 当前行为 | 接入时需要注意 |
|---|---|---|
| `PresentPage(name)` | 取已创建页面并 Push，Show 新页；默认直接 Hide 旧页 | 不自动去重；默认隐藏旧页时没有调用 `HidePage` 的附属窗口清理 |
| `PresentPage(name, false)` | 新页入栈，保留旧页活动状态 | “只显示一个页面”不是所有参数组合下的强制保证 |
| `DismissPage()` | Pop 栈顶，通过 `HidePage` 隐藏它及附属窗口，再 Show 前一页 | 返回不等于销毁，页面仍在 UI 对象表中 |
| `DismissPage(name, true)` | 弹出到指定页并包含该页，再显示剩余栈顶 | 目标必须已在栈内，需核对业务路由意图 |
| `DimissToPage(name)` | 调用 `DismissPage(name, false)`，保留并显示目标页 | API 拼写就是 `DimissToPage`；不要在示例中改写成不存在的方法 |
| `DismissAllPage()` | 反复执行 Dismiss，直至栈空 | 不表示 UI 对象表、Prefab 或 Bundle 已清空 |

Demo 的 `OpenInventory` 会先用 `IsPageInStack` 防止重复入栈，`Back` 在 Home 时不再弹出。这个保护来自大厅业务代码，不是 `PresentPage` 自带的路由去重。

页面尚未创建时，`PresentPage` 会返回 false、按名字登记延迟动作并调整资源加载顺序；仍需已有资源清单与 `CreatePage` / 资源就绪流程配合。它不是带取消、超时和代次隔离的完整异步导航器，资源重复通知或旧请求迟到时需要单独验证。

## 窗口归属：逻辑 Parent 不等于 Transform 父节点

`ShowWindow(name)` 默认把窗口的 `UIBase.Parent` 设为当前页面；`global: true` 时设为 null。这里的 Parent 是逻辑归属字段，窗口的 Transform 仍在 Window 分层下。页面切换、点击遮挡和资源持有不能只根据 Transform 层级推断。

- 同名窗口通过对象表复用，已经显示时 `ShowWindow` 直接返回；不是每次都创建新实例，也不会在显示中自动重新归属。没有当前页面时，默认调用得到的 Parent 也会是 null。
- `HidePage` 会检查所属对话框，并调用 `HideWindowsByPage` 隐藏属于该页的活动窗口。**Dismiss 返回路径会调用它，普通 Present 隐藏旧页时不会。** 因此前进和返回必须分别测试。
- `HideWindow` 会清 Parent、隐藏窗口并从打开窗口表移除。`HideWindowsByPage` 只调用窗口 Hide，没有同样清 Parent / 移除表项，不能假定两条路径的内部状态一致。
- `HideAllWindows` 遍历键的快照再关闭，避免关闭时修改字典导致异常；它也会关闭全局窗口。global 只表示不附属于具体页面，不等于不会被全局关闭。

需要对话框阻止返回、模态输入隔离或多实例窗口时，先定义自己的路由与标识契约，不能仅凭 `UIWindow` 类注释推断当前按名字索引的管理器已经支持所有行为。

## 界面生命周期与动画完成

独立 [UIBase.cs](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Scripts/GGUI/UIBase.cs)与 [UIPage.cs](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Scripts/GGUI/UIPage.cs)需要合起来看：

| 时点 | 源码顺序与责任 |
|---|---|
| 创建 / OnLoad | 管理器实例化 Prefab、登记对象后调用 OnLoad；它是框架方法，不是 Unity 自动调用的生命周期。直接使用较底层的 Create 时，不能假定完整登记和 OnLoad 已自动完成 |
| Show | 先调用 `OnPreShow`，其完成委托执行后才 `SetActive(true)`，再调用 `OnShowed` |
| Hide | 先调用 `OnPreHide`，其完成委托执行后才 `SetActive(false)`，然后调用可选的 Hide 完成回调 |
| IsShowing | 只返回 GameObject 的 `activeSelf`；不证明父级活动、实际可见、动画完成或已能接受输入 |
| 业务退出 | 取消或隔离旧异步结果、解除自己的订阅、回收实例与配对释放资产持有，需要业务明确实现 |

重写带完成委托的方法必须保证恰当时机交付一次；遗漏回调可能使隐藏无法结束，重复或过期回调也可能覆盖后续展示。`PresentPage` 的 `onShow` 在执行 Show 调用后触发，不能作为所有动画已播完的证明。

UIBase 默认补间路径会播放后立即执行完成委托，不等待补间结束；UIPage 若有约定的 AnimationClip，会通过动画事件衔接完成流程。两套代码还存在差异：独立 UIPage 添加同名动画事件前会去重，隐藏结束进入 `base.OnPreHide`；[Demo UIPage](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/Scripts/UI/UIPage.cs)仍逐次 AddEvent，隐藏结束进入 `base.OnShowed`。这需要独立动画回归，不能把无动画 Demo 的通过外推为完整转场保证。

## 隐藏、移除登记、销毁与资源释放

| 操作 | 当前边界 |
|---|---|
| Hide / Dismiss | 调整活动状态和页面栈；不是对象销毁，也没有自动完成资产 Retain / Release 配对 |
| `RemoveUIBase` | 只从对应层的对象表移除名字；没有同时移除页面栈 / 窗口归属、销毁 GameObject 或释放资源 |
| `DestroyDialog / DestroyLoading / DestroyWaiting` | 移除相应通用界面登记并 Destroy 实例；不代表其 Prefab / Bundle 已卸载 |
| 创建页面 / 窗口 | 从 ResourceSystem 查询 / 监听资产并实例化；两套 UISystem 中未见与之配套的 `Retain / DestroyObject` 资产持有管理 |
| UIPage 的组件表 | 保存 UIComponent 引用；不能据类注释认定返回页面时会自动卸载同 Bundle 组件 |
| 管理器退出 | 有资源就绪事件的退订逻辑；不等于所有页面业务订阅、在途加载、UI 表和底层资源已经整体释放 |

本轮 Demo 为大厅增加内部 `RemoveOwnedUI`：只清理仍指向该拥有者实例的登记、页面栈与窗口记录，并配合实例销毁。生命周期回归覆盖销毁后重开及另一个拥有者的 UI 登记保留；独立 GGUI 的公共 `RemoveUIBase` 仍保持上表契约。三份旧 NGUI Prefab 的修复只验收实际导入和脚本组件数量，没有验收动画视觉。

接入方应分别记录 **页面或窗口实例、Prefab / 图集等共享资产、底层 Bundle 与依赖** 的拥有者。页面隐藏可以保留实例供返回复用；确定销毁时，再按资源契约释放自己的持有，不能因一页退出就强制清空共享缓存。具体计数与统一 Group 限制见[资源管理实践](GGFramework资源管理实践.md)。

## 用 Demo 复现页面与窗口流程

按导读的[统一复现入口](GGFramework.md#运行一次完整体验)固定 Demo 并完成准备，再进入 **Play Showcase → UI** 页。示例页面由代码创建，没有完整的 UI Prefab / 动画配置。

| 操作 | 预期结果与观察点 |
|---|---|
| 初始状态 | Home 为当前页，Inventory 不在栈中，Details 隐藏 |
| 点击“进入背包”两次 | Inventory 为当前页，仍只需一次返回即可回到 Home；去重由 OpenInventory 实现 |
| 点击“打开详情窗口” | Details 显示，逻辑 Parent 为 Inventory |
| 点击“关闭所有窗口” | Details 隐藏；可以再次打开，不应出现字典修改异常 |
| 再打开 Details，点击“返回主页” | 当前页回到 Home，Inventory 与其 Details 隐藏；不应因未创建通用对话框而报错 |
| 再次进入背包 | 页面复用；本步骤需要人工确认不会残留窗口或重复事件，不能当作现有冒烟已覆盖的断言 |

行为入口见 [FrameworkShowcase.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.cs)，操作面板见 [FrameworkShowcase.GUI.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.GUI.cs)。大厅直接创建 GameObject 并添加 UIPage / UIWindow、登记并调用 OnLoad，没有走实际 UI Prefab 的异步资源创建，也没有给这些示例页面配置 AnimationClip。

## 方案取舍与不适用场景

| 选择 | 适用条件 | 代价与限制 |
|---|---|---|
| 已有 NGUI 工程评估独立 GGUI | 需要页面 / 窗口编排并能按现有后端准备 Prefab | 核对根 Tag、分层、控件绑定、动画和资源依赖，不能只复制 UISystem |
| 先运行 Demo 研究流程 | 先观察栈、窗口归属和返回行为 | 旧副本与独立模块不同；IMGUI 状态展示不能替代目标 UI 后端验收 |
| 补齐 UGUI 实现 | 项目确实需要此接口层且愿意维护适配 | 完成输入环境、布局、遮罩、补间与 Prefab 迁移后，再验证行为和编译依赖 |
| 保留现有 UI 框架 | 已有稳定路由、资源句柄和目标平台支持 | 可借鉴责任划分，比较替换成本，不必整体迁移 |

不适用于直接宣称 NGUI / UGUI 功能等价、前进和返回必然清理相同对象、同名页面自动去重、异步导航自动取消，或隐藏后资产已无泄漏释放。动画重入、快速前进返回、模态输入与共享资源释放应先形成项目契约。

## 验证方法与证据边界

### 现有证据

- [ShowcaseSmoke.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSmoke.cs)实际执行两次进入背包、显示详情、关闭全部窗口、重新显示并返回，断言当前页面与窗口状态。没有直接断言完整栈深、Parent 字段、全局窗口、动画事件次数、异步导航或资产释放。
- 独立 GGUI 当前测试目录中的 [ResourceModelTests.cs](https://github.com/gonglei007/GGFramework-GGUI/blob/12ffe13297c281cbfa6253ac443aab1552ce3857/GGUI/Assets/Tests/EditMode/ResourceModelTests.cs)验证资源模型；不能将它称为页面栈或 UGUI 集成回归。

本轮结果与未覆盖项见[运行记录](GGFrameworkUnity验证记录.md)；历史证据与 CI 的区别见导读的[证据分层](GGFramework.md#验证方法与证据边界)。本轮独立 GGUI EditMode 11/11；其后端验证仍不由大厅 IMGUI 操作代替。

### 接入前仍需验证

| 问题 | 注入与验收方法 |
|---|---|
| 页面栈是否符合路由契约 | 同名重复进入、带参数返回、空栈和保留旧页；记录栈身份、当前页与实际活动状态 |
| 窗口是否正确归属 | 分别测试前进、返回、全局窗口、无当前页和重复显示；对照 Parent、显示状态及管理表 |
| 生命周期是否唯一结束 | 有 / 无动画、快速 Show / Hide、动画中断和对象退出；记录委托次数、顺序与输入状态 |
| 旧资源结果是否会误开页面 | 延迟 / 重复资源通知，取消后重新进入，确认旧意图不会再次入栈，失败有出口 |
| 是否完成真正释放 | 统计实例、订阅、资源句柄、图集 / Bundle 持有和内存；隐藏、销毁及场景退出分别测量 |
| UI 后端是否可用 | 为 NGUI 和补齐后的 UGUI 分别测试控件绑定、输入遮挡、布局、分辨率、安全区与目标平台；不以 IMGUI 操作成功代替 |

记录 `GGUI / Demo SHA、Core、Unity、后端、平台、Prefab / 动画配置、操作序列、实际状态、回调日志和未覆盖项`，每条结论对应具体实现与运行范围。

## 图谱知识点映射

- [UI系统](../../mds/3.研发能力/3.1.6.UI系统.md)：页面栈、窗口归属、生命周期与 UI 后端。
- [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)：资源、事件和界面系统的职责划分。
- [客户端优化](../../mds/3.研发能力/3.1.3.客户端优化.md)：实例、图集与 UI 内存的实际测量。

继续阅读：[GGFramework 实践导读](GGFramework.md) · [资源管理实践](GGFramework资源管理实践.md) · [返回首页](../../README.md#可立即使用的资源)。
