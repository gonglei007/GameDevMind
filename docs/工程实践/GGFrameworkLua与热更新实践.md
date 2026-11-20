# GGFramework Lua 与热更新实践：脚本加载、互调与释放

本篇从“脚本来自哪里、C# 与 Lua 怎样互调、旧回调何时失效、退出时释放什么”出发，先复现 Demo 的本地规则执行，再对照旧 LuaManager 和内置 ToLua 源码。发布流程原理见[产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md)，系统职责见[客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)。

**项目关系与复核：** GGFramework 由本知识库作者维护；本文是工程参考。2026-11-20 完成固定源码核对与 Unity 实跑，实际结果及未覆盖项见[本轮运行记录](GGFrameworkUnity验证记录.md)。共用的[适用环境](GGFramework.md#适用条件)、[源码基线](GGFramework.md#固定源码基线)和[证据分层](GGFramework.md#验证方法与证据边界)由导读统一维护。

ToLua 来源见 Demo 固定提交内的 [readme](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/readme.txt)；本文核对该旧副本，不泛指上游当前版本。

## 适用条件

- 具备 C# 委托、Unity 对象与资源生命周期、Lua 函数 / 表 / require 基础，需要研究脚本规则、业务绑定或已有 ToLua 接入。
- 使用匹配目标平台的 ToLua 原生插件与生成绑定。Demo 的 Lua 执行来自内置 ToLua，Core 包与脚本运行时分别评估。

## 两条执行路径

| 路径 | 实际执行什么 | 未包含什么 |
|---|---|---|
| 体验大厅 Lua 页 | 每次点击创建 LuaState，用 `DoString<string>` 执行文本，再用 using 释放；默认 `128 × 2` 返回 `Lua reward: 256` | 不启动旧 GameSystem / LuaManager，不加载业务 Lua 入口、LuaLooper 或远程补丁 |
| 旧 LuaFramework 业务链 | LuaSystem.Init → 框架启动 → LuaManager；创建加载器、VM、绑定和协程支持，InitStart 再启动基础 Lua 库、Main.lua 与 Looper | 需要自己的脚本目录、绑定、原生库和业务退出契约；不是大厅按钮已经验收的链路 |

大厅代码见 [FrameworkShowcase.GUI.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.GUI.cs)，旧入口见 [LuaSystem.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/Scripts/Systems/LuaSystem.cs)和 [LuaManager.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/LuaFramework/Manager/LuaManager.cs)。本地字符串执行说明规则可以在运行时解释，不证明补丁已下载、校验、激活或可回滚。

## 脚本加载：先确认入口，再确认来源

[LuaState.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Core/LuaState.cs)构造时创建原生状态、打开基础互操作库并初始化搜索路径。`Start()` 另外加载 `tolua.lua` 等 Lua 层支持；它不是构造函数的别名。

| 入口 | 当前行为 | 接入判断 |
|---|---|---|
| `DoString<string>(text, chunkName)` | 将字符串编码后执行并转换返回值；大厅直接使用此泛型重载 | 该副本泛型路径没有普通重载的 Editor 启动检查；不能据此省略其他业务链的初始化 |
| 普通 `DoString` / `DoFile` | 普通 DoString 和文件读取入口在 Editor 检查是否已 Start；DoFile 通过 LuaFileUtils 读取字节后执行 | 把大厅代码改成普通重载或读取文件，需要重新核对启动顺序 |
| `require` / `ReLoad` | 模块有 package.loaded 缓存；ReLoad 清该模块缓存再 require | 再 require 不等于替换所有旧表、函数、委托或正在运行的协程 |
| LuaManager.InitStart | 配置路径 / Bundle，调用 Start、执行 Main.lua 并调用 Main，最后添加 LuaLooper | 当前 [Main.lua](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/Lua/Main.lua)的 Main 函数为空；不能把 InitStart 当成完整游戏业务已启动 |

### 文件、Resources 与 Bundle 的路径不同

| 加载器 | 实际选源 | 需要注意 |
|---|---|---|
| 基础 [LuaFileUtils](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Core/LuaFileUtils.cs) | beZip 为 false 时按搜索模板找文件；为 true 时从登记的 Bundle 读取 | 自身不下载、不验证版本。Editor 的 LuaState 会登记 LuaConst 的项目目录；已有路径顺序影响结果 |
| 旧 [LuaLoader](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/LuaFramework/Common/LuaLoader.cs) | 继承基础读取，beZip 取 AppConst.LuaBundleMode；AddBundle 从 Util.DataPath 加载并登记 | 当前 DebugMode、LuaBundleMode、LuaByteMode 均为 false；LuaManager 额外添加持久化 lua 路径，不等于自动下载或总是优先于内置目录 |
| 可选 [LuaResLoader](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Misc/LuaResLoader.cs) | 非 Editor：下载目录 → Resources → 基础文件；Editor：基础文件 → Resources → 下载目录 | 两个环境优先级不同；旧 LuaManager 实际 new 的是 LuaLoader，不是这个类 |

具体目录与开关见 [LuaConst.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Source/LuaConst.cs)和 [AppConst.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/LuaFramework/ConstDefine/AppConst.cs)。LuaConst.luaResDir 为 `Application.persistentDataPath/lua`；Util.DataPath 则有平台分支，不能把所有路径都当成同一下载根。线上故障应记录最终读取路径、版本与摘要，不只记录逻辑文件名。

## C# 互调：返回值、绑定与回调分别验收

| 方向 | 源码中的用法 | 验证边界 |
|---|---|---|
| C# 执行 Lua 并取值 | 大厅 `LuaResult = lua.DoString<string>(...)`，异常写入界面日志 | 只验证基础字符串规则，不修改大厅 Coins，也不证明业务绑定可用 |
| C# 调 Lua 函数 / 表 | LuaManager.GetFunction / GetTable；取 LuaFunction 后 Call / LazyCall，或通过 Util.CallMethod 按名字调用 | 取得的跨语言引用需要配对 Dispose，不能把返回对象当成无所有权的普通缓存 |
| Lua 调 C# | 旧 LuaManager 显式执行 LuaBinder.Bind、DelegateFactory.Init 与 LuaCoroutine.Register | 依赖生成 Wrap、委托适配和目标平台原生库；不是任意新增 C# API 都能直接使用 |
| Lua 回调 Unity 组件 | [LuaBehaviour.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/LuaFramework/Common/LuaBehaviour.cs)按对象名字转发 Awake / Start / 点击，AddClick 保存 LuaFunction 并设置 NGUI 监听 | 是该类的约定，不代表 Lua 函数会自动获得全部 MonoBehaviour 生命周期 |

[LuaBinder.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Source/Generate/LuaBinder.cs)登记了 GameSystem、ResourceSystem、UnityEngine.GameObject 等包装；大厅没有执行这一整套业务绑定。增加或修改 C# 接口时，应核对导出配置、重新生成绑定，再在目标构建验证，不能仅凭 Editor 编译通过认定 AOT 接入完成。

`GetFunction` 命中缓存仍会 AddRef。[LuaBaseRef.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Core/LuaBaseRef.cs)的 Dispose 先减引用计数，再按条件交回 VM 引用；终结器也不等于立即清理。旧 LuaManager.CallFunction 取函数后直接 LazyCall，未显式 Dispose，应在接入审查中补清这类便捷调用的责任，不能把存在包装方法当成引用平衡的证明。

手动使用 [LuaFunction.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Core/LuaFunction.cs)的 BeginPCall / PCall / EndPCall 时还要保证栈配对和异常出口。Lua 执行是同步调用，界面捕获异常不代表有超时、取消、事务回滚或不受信任脚本的隔离保障。

## 脚本生命周期与资源释放

### 临时解释器与常驻脚本系统

大厅 RunLua 每次 using 一个新状态，正常返回或执行抛错后退出该作用域并 Dispose；上一次 VM 的全局变量不会作为下一次执行的业务状态保留。需要跨帧逻辑、定时器或状态保留时，应评估常驻 VM，而不是把按钮示例直接改成长期业务入口。

旧 LuaManager 添加 [LuaLooper.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Misc/LuaLooper.cs)，驱动 Lua Update / LateUpdate / FixedUpdate，并处理引用收集。关闭前要停止事件、协程和异步结果进入旧 VM；对象回池、界面关闭和场景退出也要分别解除它们持有的 Lua 回调。

### 关闭一个 VM 不等于只清一个局部对象

LuaState.Dispose 清理引用表、关闭原生 lua_State、清翻译器映射，最后还调用 **共享的 LuaFileUtils.Instance.Dispose**。后者会清搜索路径并对其 zipMap 中的 Bundle 执行 **Unload(true)**。因此“不同 LuaState”不等于完整资源隔离：不要在已运行 LuaManager 的同一进程中直接套用大厅的每次 using 流程，除非已明确共享加载器与 Bundle 的所有权。

| 对象或操作 | 实际释放范围 | 接入方仍需处理 |
|---|---|---|
| LuaFunction / LuaTable Dispose | 释放跨语言引用的持有 | 先从 C# 事件、按钮和定时器移除调用入口，再按持有次数释放；关闭 VM 后不再调用旧句柄 |
| LuaState.Dispose | 关闭 VM、清引用 / 映射，并清共享加载器 | 不代表所有 Unity 实例或 GGResource 缓存都已释放；保留业务资产与实例的独立所有权记录 |
| LuaManager.Close | 调用 loop.Destroy，再 Dispose VM 并置空字段 | 缺少完整重复关闭 / 未初始化保护；Looper.Destroy 只清事件和 luaState，不销毁组件，宿主需确保驱动已停用或移除 |
| LuaBehaviour.RemoveClick / ClearClick | 释放字典保存的 LuaFunction | 当前实现没有同时清 UIEventListener.onClick；需避免监听器继续调用已释放函数 |
| LuaBehaviour.OnDestroy | 对持有 Bundle 执行 Unload(true)，清点击引用并调用 ClearMemory | 不能用于不加区分地卸载共享 Bundle；也没有自动转发同名 Lua OnDestroy |
| GC / ClearMemory | 请求 C# GC、未用资产卸载与 Lua GC | 不是显式退订、业务退出或资产引用计数的替代品 |

ToLua 的 [LuaClient.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/ToLua/Misc/LuaClient.cs)模板另有 OnApplicationQuit 调用、场景通知退订与 Destroy 路径；旧 LuaManager 并非其子类，不能把模板的退出行为自动套到旧业务链。释放资产时继续遵循[资源管理实践](GGFramework资源管理实践.md)和 [UI 管理实践](GGFrameworkUI管理实践.md)中的实例、共享资产与 Bundle 分工。

## 本地执行与生产热更新的边界

| 看到的现象 | 可以说明什么 | 不能据此认定什么 |
|---|---|---|
| 修改文本后结果变化 | 当前 VM 可以解释新规则并向 C# 返回值 | 补丁已打包、发布或下载；C# 二进制代码已被替换 |
| 本地文件优先读取 | 加载器允许按配置选择某个来源 | 文件可信、版本匹配、资源完整或能恢复坏补丁 |
| 编辑器监听文件刷新 | LuaSystem 在 Editor 监听文件变化，调用 LuaRefreshScript | 真机自动更新、全量状态迁移或安全回滚 |
| 清 package.loaded 后 require | 重新加载模块入口 | 所有旧闭包 / 委托 / 协程已经替换或取消 |
| 大厅其他页能加载本地 Bundle | 特定资源路径能在本机运行 | Lua 补丁的发布、切换与回退也已验收 |

编辑器 [LuaRefreshScript.lua](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/LuaGame/Lua/Framework/LuaRefreshScript.lua)只按特定控制器 / 视图约定清缓存并重建关系，不是通用状态迁移器。LuaSystem 的 FileSystemWatcher 在该类中未见 Dispose，变化列表也没有跨线程同步；不能把这个开发辅助路径当成生产补丁管理器。

旧 [GameSystem.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/ggsource/Scripts/Systems/GameSystem.cs)有解包、PackageSystem 更新 table / asset 及初始化 Lua 的阶段，部分失败分支仍有 TODO。大厅绕过该启动流程，不能用大厅冒烟证明这些阶段已完成生产验收。

生产接入至少要另行落实：可信版本清单与内容校验，脚本 / 资产 / C# API 的兼容约束，独立版本目录及完整后再激活，入口健康检查和上个可用版本恢复，以及旧异步结果失效、下载中断恢复和补丁观测。目录里存在一个新 lua 文件不等于版本已经安全切换。

## 用 Demo 复现规则执行

按导读的[统一复现入口](GGFramework.md#运行一次完整体验)固定 Demo 并完成准备，再进入 **Play Showcase → Lua** 页。此页不启动 LuaManager 业务链，也不从公网下载补丁。

| 操作 | 预期与观察点 |
|---|---|
| 默认文本点击“执行 Lua” | 显示 `Lua reward: 256`；这是现有冒烟直接断言的结果 |
| 把默认表达式 `coins * 2` 改为 `coins * 3` 再执行 | 预期显示 `Lua reward: 384`；局部 coins 不改变大厅 Core 页 Coins |
| 改为 `counter = (counter or 0) + 1; return tostring(counter)`，执行两次 | 预期每次为 `1`，说明每次新建 VM，不保留上次全局变量 |
| 输入语法错误，再恢复默认代码 | 预期显示“Lua 执行失败”及原因，恢复后能再次得到 256；本轮新增生命周期回归已执行错误恢复，原有冒烟只覆盖默认结果 |

后三项本轮已由新增生命周期回归通过真实 RunLua API 执行：384、两次全局变量均为 1、语法错误后恢复 256。测试通过反射设置私有脚本文本，没有模拟鼠标编辑输入框；逐轮结果见[运行记录](GGFrameworkUnity验证记录.md)。

## 方案取舍与不适用场景

| 选择 | 适用条件 | 代价与限制 |
|---|---|---|
| 大厅式临时 VM | 可信本地基础规则实验，主要观察返回值 | 不保留业务状态；每次建 VM 有成本，还要考虑共享加载器副作用 |
| 常驻 LuaManager / ToLua | 已有 Lua 业务，需要跨帧驱动及 C# 绑定 | 管理绑定、回调引用、版本兼容、退出顺序和目标平台原生库 |
| 本地刷新辅助开发 | 明确使用现有控制器 / 视图约定，在 Editor 迭代 | 旧引用、线程同步与监听器清理需补齐；不替代生产发布 |
| 保留 C# 或现有脚本方案 | 逻辑简单或团队已有成熟管线 | 可借鉴职责划分；不必为“可热更”迁入整套旧依赖 |

不适用于直接执行不受信任的远程代码、把修改本地文本当成生产热更新验收、用 GC 代替事件退订，或宣称所有脚本与资源可无状态迁移地原地替换。需要字节码时，也应另外验证 Lua 运行时、原生库与目标架构的兼容性。

## 验证方法与证据边界

- [ShowcaseSmoke.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSmoke.cs)只调用 RunLua 并断言默认结果为 `Lua reward: 256`；没有直接断言文件选源、双向业务绑定、模块重载、句柄平衡、退出泄漏或补丁回滚。

本轮结果与未覆盖项见[运行记录](GGFrameworkUnity验证记录.md)；历史证据与 CI 的区别见导读的[证据分层](GGFramework.md#验证方法与证据边界)。本轮运行的是 Demo 内置 ToLua 的临时 VM 路径；未验收 LuaManager 业务链、LuaFunction / LuaTable 全量句柄平衡或真实补丁发布。

| 接入待验项 | 注入与通过条件 |
|---|---|
| 文件与模块来源 | 同名文件、多搜索根、Editor / Player、文件缺失、Bundle 模式；记录实际来源与摘要，错误有明确出口 |
| C# 双向互调 | 目标 Player 中验证类型、参数 / 返回值、委托、缺失绑定与异常；明确每个 LuaFunction / LuaTable 的拥有者 |
| 引用与退出 | 重复开关界面、点击监听移除、协程中退出、迟到结果、多 VM 共存；旧入口不再调用失效句柄，共享 Bundle 不被误卸载 |
| 版本切换 | 脚本 / 资产 / C# 接口不兼容、旧闭包与回调仍在途；按预定边界停用旧代次，避免混用新旧对象 |
| 补丁完整性与恢复 | 清单 / 内容错误、断网、空间不足、激活中断、入口异常；不激活半成品，能恢复上个可用版本并留下日志 |
| 性能与平台 | 目标设备测建 VM、跨语言调用、GC 与内存峰值；核对原生插件架构、生成绑定和构建后端，不外推 Windows 结果 |

保存 `Demo SHA、ToLua / 原生库来源、Unity、平台与后端、绑定配置、脚本与资产版本 / 摘要、加载来源、操作序列、引用 / 回调记录和未覆盖项`，让“本地可执行”和“生产可发布”各有对应证据。

继续阅读：[GGFramework 实践导读](GGFramework.md) · [产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md) · [资源管理实践](GGFramework资源管理实践.md) · [Core 基础能力实践](GGFrameworkCore基础能力实践.md) · [返回首页](../../README.md#可立即使用的资源)。
