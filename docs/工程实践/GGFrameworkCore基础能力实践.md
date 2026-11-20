# GGFramework Core 基础能力实践：状态、订阅、复用与退出

本篇从“状态为什么没切换、退订何时生效、对象归还后还剩下什么、退出时谁停止工作”出发，用 Demo 观察 Core 基础能力，再核对实现与测试。架构定位见[客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)，模式与所有权原理见[设计模式](../../mds/1.基础能力/1.2.1.设计模式.md)和[内存管理](../../mds/1.基础能力/1.1.6.内存管理.md)。

**项目关系与复核：** GGFramework 由本知识库作者维护；本文是工程参考。2026-11-20 完成固定源码核对与 Unity 实跑，实际结果及未覆盖项见[本轮运行记录](GGFrameworkUnity验证记录.md)。共用的[适用环境](GGFramework.md#适用条件)、[源码基线](GGFramework.md#固定源码基线)和[证据分层](GGFramework.md#验证方法与证据边界)由导读统一维护。

<a id="适用条件与版本"></a>

## 适用条件

- 具备 C# 委托、泛型、Unity 组件与主线程基础，需要组织轻量流程、模块事件、短生命周期实例或统一退出责任。
- Core 是零第三方依赖的 UPM 包，但包内有 Unity API；不要把“普通托管对象”理解为整个包可以脱离 Unity 直接运行。

| 核对对象 | 版本基线 | 本篇范围 |
|---|---|---|
| Core 稳定版 | `v0.3.0`，标签对应 [c0567a8](https://github.com/gonglei007/GGFramework-Core/tree/c0567a89ebf3837754eaf504ae10e93a184ea146) | 状态机、事件总线、两种对象池、单例、任务及主线程派发 |
| Core 开发分支 | [7e0fa45](https://github.com/gonglei007/GGFramework-Core/tree/7e0fa45c3b514fde135d04f5449a2e0bc9202b4a)，包版本 `0.4.0-preview.1` | 相对稳定版新增资源缓存 / 请求队列等；本文所核对的上述 Runtime 文件未变，不将预览能力算入 Demo |
| 集成 Demo | [e2a7586](https://github.com/gonglei007/GGFramework-Demo/tree/e2a7586a1325fc8dd762b55d1105de81b9825154) | [manifest](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Packages/manifest.json)固定 Core `v0.3.0` 并启用包测试；Core 页直接调用该 UPM 包 |

Core 的这些类型位于 `GGFramework.Core`；`Singleton<T> / SingletonLifetime / CoroutineUtil` 仍在全局命名空间，`TaskSystem / GTask` 在 `GGFramework.GGTask`。引入包前检查旧同名副本与程序集引用，避免与 `UnityEngine.Pool`、旧单例或第三方状态机混用。其他业务模块的版本与源码副本仍按各自 manifest 核对。

## 状态机：同步转移与守卫的范围

[StateMachine.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/StateMachine.cs)是普通对象，不会自动接收 Unity Update。Demo 在自己的 Update 中调用 `Machine.Update(Time.deltaTime)`，并以金币数量守卫 `Idle → Running`。

| 调用或条件 | 当前行为 | 接入时需注意 |
|---|---|---|
| `Configure(state, ...)` | 注册或覆盖该状态的进入、退出和更新委托 | 不会自动进入该状态；未传的回调也会被覆盖为 null |
| 首次 `ChangeState(next)` | 设置 Current / HasState，调用 OnEnter，再发 StateChanged；previous 为类型默认值 | 未进入时 Current 也为默认值，应配合 HasState 判断 |
| 后续转移 | 先检查同状态与已登记守卫，再 OnExit → 设置新状态 → OnEnter → StateChanged | 同步执行；不是异步进入流程或自动转移队列 |
| 同状态或守卫拒绝 | 返回 false，不执行正常转移回调 | false 不只表示“条件不足”，也可能是重复进入 |
| 没有该条守卫 / 目标未 Configure | 仍可转移，缺失的回调不执行 | 守卫是针对特定 from / to 的限制，不是默认拒绝的白名单 |
| `Update(dt)` | 只转发当前状态的更新委托 | 宿主决定何时驱动、是否暂停，以及使用何种时间 |
| `Clear()` | 清状态回调、守卫和当前状态 | 不调用 OnExit，也不清 StateChanged 的事件订阅 |

实现没有转移重入保护、异常隔离或回滚：例如 OnEnter 抛错时 Current 已经改变，后续 StateChanged 未必执行。不要假定它能在回调异常后恢复原状态；在回调内再发起转移也需单独定义顺序并测试。退出业务时若需要 OnExit，应由宿主显式组织，不能只依赖 Clear。

## 事件订阅：快照派发与订阅者所有权

[EventBus.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/EventBus.cs)按泛型事件类型保存委托，实例之间隔离。Demo 的 `Events` 由大厅实例拥有，通过具名方法 `OnCoins` 订阅 `CoinEvent`，不是全局自动收集组件的事件系统。

- 同一类型、相等委托的重复 Subscribe 会去重；Unsubscribe 应使用原委托。反复创建捕获不同上下文的 lambda，不等于能用另一个 lambda 退订。
- Publish 在调用线程同步执行，并复制当前订阅列表。派发中新增订阅不会加入本轮；退订或 Clear 也不会移除已经进入快照的处理器。退订影响后续发布，不是撤销正在发生的通知。
- 单个处理器异常会记录到 Unity 日志，再执行后续处理器；没有事务回滚，之前的业务副作用仍在。
- 没有弱引用、自动随 GameObject 销毁退订、线程同步或自动切回主线程。长生命周期总线会持有委托及其目标；UI 退出或对象回池时需要按所有权解除订阅。
- Clear 会清该总线所有订阅。Demo 可以在 OnDestroy 清自己拥有的 Events；共享总线的单个消费者应只退订自己的处理器，不能替其他模块清空。

对池化对象还要区分“组件创建”“每次取用”“每次归还”“最终销毁”：如果每次取出都订阅，就应在每次归还时配对退订。仅等 OnDestroy 处理，会让空闲对象继续响应事件；同一委托去重也不能代替跨租用周期的数据重置。

## 对象池：空闲容量不是总实例上限

[ObjectPool.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/ObjectPool.cs)提供两种基于 Stack 的池，均不维护使用中对象集合。Demo 另有 `active` 列表，池的 `CountInactive` 只统计空闲项。

| 能力 | `Pool<T>` | `GameObjectPool` |
|---|---|---|
| 创建与预热 | 工厂创建引用类型，预热数量限制在 0 到 maxSize；预热不调用 onGet / onRelease | 从 Prefab 克隆，预热后停用，可挂在 root 下 |
| Get | 弹出空闲项，空时创建，然后调用 onGet | 弹出空闲项，失效 Unity 对象则重新创建，然后 SetActive(true) |
| Release | 忽略 null，先 onRelease，再按空闲容量决定是否存回 | 停用、挂回 root；空闲容量已满则销毁 |
| 超过 maxSize | 丢弃归还对象，不提供独立的 onDestroy 回调 | 播放中 Destroy，非播放态 DestroyImmediate |
| Clear | 仅清空闲项，逐项再次调用 onRelease | 仅销毁空闲 GameObject |

maxSize 限制的是**保留的空闲数量**，Get 不会因此限制同时借出的数量。Demo “使用中少于 8 才可取出”的按钮判断属于界面业务，不能据此认定池已实现硬容量门禁。

两种池都不校验归属或重复归还；同一对象归还两次可能被当成两个空闲项，再同时借给不同消费者。池根也不是完整的所有权账本。接入方应跟踪借出集合，拒绝重复 / 外来归还，并重置业务字段、Transform、订阅、特效和旧异步结果。

泛型池的 onRelease 在归还时执行，Clear 又会对这些空闲对象执行一次，清理逻辑应能承受该顺序；不能把它当成只调用一次的析构函数。回调异常也没有隔离与自动补偿。管理原生句柄或 Unity 资源时，丢弃引用、停用 GameObject 与真正释放资产是不同操作，另见[资源管理实践](GGFramework资源管理实践.md)。

## 退出生命周期：标志、任务与实例分别处理

### 单例退出守卫的实际触发条件

[Singleton.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/Singleton.cs)把 IsQuitting 放在非泛型静态类 SingletonLifetime，所有闭合泛型共享。标志为 true 时 Instance 返回 null，避免退出期间重新创建单例。

当前基类在 **OnDestroy** 中设置标志，不只是在 OnApplicationQuit 中设置；因此普通销毁也可能阻断其他单例的后续访问。派生类有自己的销毁方法时还需核对清理链；例如 TaskSystem 的 OnDestroy 没有显式调用基类退出逻辑。不能把这个布尔值当成整个工程已经协调完成退出的证明。

自动创建的单例仅在播放态调用 DontDestroyOnLoad，查找到的已有场景实例不会在该分支被自动设为常驻。Instance 内部虽然有 lock，仍会查找和创建 Unity 对象，不能从工作线程用它初始化组件。Demo 在 Awake 主动把 IsQuitting 设回 false，以支持再次进入播放；实际项目应由新会话的统一入口管理复位，不在任意业务访问中绕过退出守卫。

### 停止驱动不等于取消已启动工作

| 实现 | 已有行为 | 退出责任 |
|---|---|---|
| [MainThreadDispatcher](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/MainThreadDispatcher.cs) | Post 在已记录的主线程立即执行，否则入队；Enqueue 始终入队；ProcessQueue 排空并隔离队列回调异常 | 主线程先 Initialize 并创建宿主，才能依赖每帧泵。静态 Post 不自动创建宿主；Initialize 不清队列，ProcessQueue 也不强制校验线程 |
| [TaskSystem](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/TaskSystem.cs) | Init 防重复泵；宿主 OnDestroy 设置 stopping，队列超时后可推进下一项 | 不强制取消已开始的工作，不保证退出前排空；超时后旧任务可能仍在运行，工作函数需自行支持终止或结果失效 |
| [CoroutineUtil](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Runtime/CoroutineUtil.cs) | 在自身单例上运行协程，完成后调用委托；DoCoroutine 不返回取消句柄 | 销毁调用方或调用方 StopAllCoroutines，不等于停止另一个宿主上的协程；完成回调需检查拥有者是否仍有效 |

MainThreadDispatcher 是独立 MonoBehaviour，不继承 Singleton<T>，没有相同的 IsQuitting 检查。队列异常隔离也不覆盖 Post 在主线程直接执行的分支。接入时应先停止产生新工作，再让既有结果取消或失效，最后释放消费者；不要在退出时再次懒创建宿主。

### Demo 做了哪些清理

[FrameworkShowcase.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.cs)的 OnDestroy 先置 disposed，停止大厅自身协程、终止当前 HTTP、释放本地服务与资源入口、退订外部事件，再清自己的 Events、按实例身份移除所属 UI 登记及路由，归还 active 中的对象并清池，释放示例缓存持有。

后台与 CoroutineUtil 的完成委托会检查 disposed 后再更新大厅。这个检查阻止已销毁大厅接收结果，**没有取消底层计算或全局协程，也没有排空所有静态队列**。OnDestroy 未调用 Machine.Clear；状态机回调及 StateChanged 仍需按对象是否继续被外部持有来判断释放责任。不要把示例清理路径扩大为跨场景、跨会话或进程退出的全局保证。

## 用 Demo 复现 Core 页

按导读的[统一复现入口](GGFramework.md#运行一次完整体验)固定 Demo 并完成准备，再进入 **Play Showcase → Core 基础** 页。该页使用稳定 Core 包，不执行预览版资源契约。

| 操作 | 预期与观察点 |
|---|---|
| 金币为 0 时点击“进入 Running” | 守卫拒绝，仍为 Idle；不是错误日志或自动排队等待 |
| 点击“发布金币 +1”，再进入 Running | Coins 增加，转移成功；重复进入同状态返回拒绝 |
| 点击“取消订阅”，再次发布 | Coins 不变；恢复订阅再发布后增加 |
| “取出对象 → 归还对象 → 再取出” | 比较日志 instanceID，复用同一对象；使用中与空闲数量分别变化 |
| 点击“后台计算 → 主线程回调”和“协程延迟完成” | 观察各完成计数和线程记录；等待完成不等于退出时会自动取消 |
| 工作未完成时退出，再进入播放 | 本轮新增生命周期回归已断言旧结果不写回、退订、池实例销毁与重开；完整播放两轮也通过，仍不等于取消底层任务 |

按钮与顺序见 [FrameworkShowcase.GUI.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.GUI.cs)。Demo 预热 3 个、最多缓存 8 个对象，业务状态守卫只有 `Idle → Running`；不要从这一个守卫外推出完整状态合法转移表。

## 方案取舍与不适用场景

| 选择 | 适用条件 | 代价与限制 |
|---|---|---|
| Core 轻量状态机与总线 | 流程规模有限，宿主能明确驱动与管理订阅 | 自行补齐业务合法转移、重入 / 异常策略和生命周期 |
| Core 对象池 | 需要简单实例复用，并能跟踪借出归还 | 不提供归属检测、硬并发上限、资产引用计数或线程安全 |
| 使用 Demo 先研究协作 | 需要可观察的守卫、退订、身份复用与异步回调 | 只证明给定体验路径；历史测试与当前接入环境分开验收 |
| 保留现有成熟框架 / Unity 原生能力 | 已有可靠状态、事件、池或退出约定 | 可只参考职责划分；比较类型冲突、替换成本与长期维护 |

不适用于直接作为多线程事件中心、带回滚的异步工作流、严格容量与归属保护的资源管理器，或保证所有任务退出完成的服务容器。层级状态机、持久化事件、超时取消、资产卸载和跨场景会话隔离应另行设计；预览版资源队列也不应被当成稳定版对象池的现成功能。

## 验证方法与证据边界

| 已有证据 | 实际覆盖 | 未证明什么 |
|---|---|---|
| [StateMachineTests.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Tests/StateMachineTests.cs) | 同状态拒绝、进入退出顺序、StateChanged、守卫、Update、未配置状态和复位 | 回调重入、异常回滚或异步转移 |
| [EventBusTests.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Tests/EventBusTests.cs) | 类型隔离、去重、退订、顺序、派发中退订与单处理器异常隔离 | 跨线程发布、自动退订、弱引用或业务副作用回滚 |
| [ObjectPoolTests.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Tests/ObjectPoolTests.cs) | 两种池的复用、泛型重置 / 预热 / 空闲上限与 Clear、GameObject 激活 | 重复归还、外来对象、在用对象清理或目标平台内存收益 |
| [SingletonLifetimeTests.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Tests/SingletonLifetimeTests.cs) | 共享标志可设、退出标志为 true 时 Instance 返回 null | 实际销毁顺序、完整单例创建 / 销毁链或关闭域重载后的多轮播放 |
| [TaskSystemTests.cs](https://github.com/gonglei007/GGFramework-Core/blob/c0567a89ebf3837754eaf504ae10e93a184ea146/Tests/TaskSystemTests.cs) | 重复 Init 与超时任务不阻塞后一任务 | 工作函数真正取消、退出前排空或结果代次隔离 |
| [ShowcaseSmoke.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSmoke.cs) | 守卫拒绝后成功、金币退订、对象身份复用、协程 / 后台完成计数和主线程观察 | 在工作中退出、泄漏检测、重复播放与性能基准 |

Core 包测试默认不在消费工程运行，需要 manifest 的 `testables` 含 `com.gonglei.ggframework.core`；Demo 已配置，运行与报告要求见[统一复现入口](GGFramework.md#运行一次完整体验)。稳定包本轮 EditMode 66/66；新增生命周期覆盖退出后的事件、池与迟到结果。具体环境和逐项证据见[运行记录](GGFrameworkUnity验证记录.md)，不外推到预览版或全部共享单例。

后续[自动化 CI](GGFramework自动化回归与CI.md)在 Core 仓库为预览包另建 Unity 宿主，独立执行至少 104 项；Demo 仍测试它自己固定的稳定包。两条测试结果分别记录 SHA 和 artifact，不用预览版结果替代稳定版接入验证。

| 项目待验项 | 注入与通过条件 |
|---|---|
| 状态转移契约 | 同状态、未登记路径、回调重入和进入 / 退出异常；记录 Current、回调顺序和明确的失败恢复策略 |
| 订阅生命周期 | 反复启停、池化取还、派发中退订 / 清总线、旧对象迟到结果；退出后后续发布不再命中已失效消费者 |
| 池所有权与容量 | 重复 / 外来归还、超过缓存上限、借出时 Clear、重置回调异常；每个借出实例只有一个有效拥有者 |
| 退出和重复播放 | 场景卸载、普通单例销毁、工作中退出、域重载开 / 关；检查共享退出标志、静态队列、事件数与存活对象 |
| 实际性能收益 | 在目标设备比较分配、GC、帧耗时与内存峰值，同时确认空闲缓存预算；不以 instanceID 相同代替性能测量 |

保存 `Core / Demo SHA、包锁定记录、Unity、平台与后端、域重载设置、操作序列、事件 / 状态 / 对象标识、日志与未覆盖项`。每条结论对应运行环境，不能由 Windows Mono 外推到移动端、WebGL 或 IL2CPP。

继续阅读：[GGFramework 实践导读](GGFramework.md) · [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md) · [资源管理实践](GGFramework资源管理实践.md) · [返回首页](../../README.md#可立即使用的资源)。
