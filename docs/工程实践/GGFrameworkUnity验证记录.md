# GGFramework Unity 实跑记录（2026-11-20）

本记录保存实践系列的一次实际运行与修复回归，区分 Demo 集成路径、独立模块测试和项目接入验收。它不替代各模块 API 手册。阅读入口：[GGFramework 实践导读](GGFramework.md)。

后续已整理为[自动化回归与 CI 复现](GGFramework自动化回归与CI.md)。本页保留首次实跑时的环境、源码和“当时尚无 CI”等观察；自动化后的执行契约与运行证据另行维护，不改写历史报告。

## 环境与隔离方式

- 系统：Windows 11 Pro `10.0.26300`，x64；Unity `6000.3.13f1 (8c4f11e4fb20)`。
- Editor 图形设备：Direct3D 11.0（feature level 11.1），NVIDIA GeForce RTX 4060 Ti。Windows Player 为 Mono Development，实际以 `-batchmode -nographics` 运行，未生成视觉验收截图。
- 从实践导读固定的提交建立独立 Git 克隆和全新 Library，按各工程原有 manifest 解析 UPM；没有复制原工程的 Library，也没有覆盖原工程中的在制修改。
- 原始报告目录：本机 `D:/Works/GGValidation/ggf-practice-20261120/reports/`。入库的脱敏断言、NUnit 用例清单、时间与原始文件 SHA-256 见[机器可读结果](验证记录/GGFramework-2026-11-20/results.json)。公开文本副本只替换工程路径前缀、去除行尾空白，原始文件不变并单独计算摘要。完整 Unity 日志包含机器与授权信息，保留本机，不公开上传。
- 全部通过批处理调用真实 Unity API。生命周期 Editor 回归启用图形设备；无图形设备尝试单独记录失败，不能用已通过的业务断言掩盖 Editor 错误。Player 的后端、图形模式与结果单独记录。
- Demo Core 包固定 `v0.3.0 / c0567a89ebf3837754eaf504ae10e93a184ea146`；独立 GGResource、GGNetwork、GGUI 使用 `v0.1.1 / a5395876d2e7`，GGUser 使用 `v0.2.0`，没有统一升级依赖。

## 结果与证据

初始 Demo 为 `3039f9aad1813b8ad72e373a30b3eb073e0ee2eb`，初始 GGNetwork 为 `a80eaa7a55fa29fb700fd8b12e78ab290a0fc37d`；其他模块保持导读基线。修复源码分别经 [Demo PR #1](https://github.com/gonglei007/GGFramework-Demo/pull/1) 与 [GGNetwork PR #1](https://github.com/gonglei007/GGFramework-GGNetwork/pull/1) 合并，导读已固定到新提交。实际受测代码分别交付在 `1e56632d884331ad2fe62eceb0df79e8934d27b5`、`98779c641c9352bfe131e02553a76a0a1d167e36`；合并提交为 `e2a7586a1325fc8dd762b55d1105de81b9825154`、`7e371eab8b9de00f06e713ca7bd8468ebb890ea0`。提交后核对受测源码与提交一致，Unity 自动生成的用户 / Editor 设置变化未混入修复。

| 对象与执行入口 | 实际结果 | 可以说明的范围 |
|---|---|---|
| 原始 Demo 的 Core EditMode | 66 通过，0 失败，0 跳过；退出码 0 | 稳定包当前测试；不覆盖 Core 预览版 |
| 原始 Demo 完整 Editor 冒烟 | 28/28；退出码 0 | 大厅操作的 API 路径，含 Editor Simulation 和本地真实 Bundle |
| 独立 GGResource EditMode | 15 通过，0 失败，0 跳过；退出码 0 | 缓存、类型、引用计数等现有内存态测试，不等于完整 Loxodon 异步发布链 |
| 独立 GGUI EditMode | 11 通过，0 失败，0 跳过；退出码 0 | 现有模块断言；不证明 UGUI 与 NGUI 完整等价 |
| 独立 GGUser EditMode | 71 通过，0 失败，0 跳过；退出码 0 | 假渠道、网关及本地状态契约，不是真实渠道验收 |
| 独立 GGUser PlayMode | 11 通过，0 失败，0 跳过；退出码 0 | 当前用户 / 管理器生命周期用例，仍为本地测试依赖 |
| 独立 GGNetwork 修复后 EditMode | 162 通过，0 失败，0 跳过；退出码 0 | 包含 2 项缺失依赖回归；没有安装并测试可选 BestHTTP |
| 修复后 Demo Core / Editor 冒烟 | Core 66/66、冒烟 28/28；退出码均为 0 | 最终源码的必要回归；Core 数量不重复计入模块合计 |
| 修复后关闭 Domain Reload 连续播放 | [第一轮](验证记录/GGFramework-2026-11-20/demo-no-domain-reload-fixed-cycle-1.txt)、[第二轮](验证记录/GGFramework-2026-11-20/demo-no-domain-reload-fixed-cycle-2.txt) 各 35/35；退出码 0，完成两次 Play Mode 退出并恢复设置 | 包含同会话销毁 / 重开、UI 归属、资源、池、事件与迟到结果 |
| Windows x64 Mono Development Player | 构建退出码 0；[冒烟 27/27](验证记录/GGFramework-2026-11-20/demo-player-smoke-final.txt)、[生命周期 35/35](验证记录/GGFramework-2026-11-20/demo-player-lifecycle-final.txt)，退出码均为 0 | Player 不含 Editor Simulation；无图形模式只验 API / 生命周期 |

最终按模块去重合计 **336 项 NUnit 用例通过、0 失败、0 跳过**。NUnit 数量按 XML 根节点统计；生命周期报告中的 `PASS` 是集成断言数量，不能与 NUnit 用例数混算。首次导入耗时计入运行器起止时间，不能据此比较模块性能。

保留的反向证据包括[UI 清理前失败](验证记录/GGFramework-2026-11-20/demo-lifecycle-before-fix.txt)、[关闭 Domain Reload 第二轮失败](验证记录/GGFramework-2026-11-20/demo-no-domain-reload-before-cycle-2.txt)和[无图形 Editor 的环境错误](验证记录/GGFramework-2026-11-20/demo-lifecycle-fixed-headless.txt)。初始导入被中断且缺少退出记录的尝试在 JSON 单列，未算作通过。两个源码仓库检查时均无 Actions 工作流、main 保护或 ruleset 必需检查；它们的本机 Unity 报告与本知识库的 17 项 CI 门禁分别核对。

## 实际发现与修复

### Demo 退出后留下 UI 登记

在显示 Inventory 和 Details 后销毁大厅根对象，原始实现仍在常驻 UISystem 中保留 Home、Inventory、Details 的登记。同名登记会阻止同一会话重开；只销毁 GameObject 不足以清理管理器中的托管引用。

修复由大厅保存自己创建的 UI 实例，退出时按名字和实例身份移除登记、页面栈与窗口记录，再销毁所属实例。重新打开时按需创建层组。回归还保存另一个拥有者的窗口登记，确保退出不会清空其他业务 UI。这是 Demo 副本的定向清理，不改变独立 GGUI 的公共 `RemoveUIBase` 契约。

### 关闭 Domain Reload 后第二轮资源加载失败

同一 Editor 进程中连续进入、退出 Play Mode 两次：第一轮通过，第二轮首次加载资源失败。Demo 内置 Loxodon 的 Executors 在退出时把静态 `disposed` 设为 true，重建执行器时没有恢复，后续协程请求走已关闭分支。

补丁保留第三方版权，在主线程成功创建新执行器后恢复派发。回归运行两个完整播放周期，记录每轮断言，并恢复调用前的 Editor 播放设置。此修改只进入 Demo 内置副本；不推断其他仓库中的第三方副本已经同步修复。

### 三个旧 NGUI Prefab 的脚本引用无效

全新导入发现 `UISwitch_AllComplete`、`UISwitch_in`、`UISwitch_out` 含 `m_Script: {, type: 3}`。按序列化字段与仓库中的 `.meta` GUID 恢复 UISprite / UIWidget 引用，没有删除组件来消除错误。Unity 实际导入检查每个 Prefab：8 个 UISprite、1 个普通 UIWidget、0 个缺失脚本。该检查不验收过场动画视觉与输入行为。

### 独立 GGNetwork 默认检出无法编译

原始工程默认使用 UnityWebRequest，却无条件编译没有随仓库提供的 BestHTTP 类型。修复把旧适配器和 EagleEye 的 BestHTTP 实现放在 `GGNETWORK_BESTHTTP` 宏后；默认工程无需安装该插件。显式选择未安装的后端会明确失败，EagleEye 保持关闭。可选插件本身仍需安装兼容版本并配置程序集引用后单独验收。

## 复现方法

先按导读固定源码提交，用 Unity 6000.3.13f1 打开对应工程，等待包解析完成。Demo 先执行 **GGFramework → Demo → Build Sample Bundles**。生命周期入口为 **Run Lifecycle Checks**；两轮入口为 **Run Lifecycle Checks Twice Without Domain Reload**，也包含修复 Prefab 的实际导入检查。

批处理从 Demo 仓库根运行，`$editor` 指向已安装的 Unity，`$project` 为 `unity_project` 的绝对路径。以下生命周期命令启用图形设备，不传 `-nographics` 或 `-quit`，由回归在真正退出 Play Mode 后结束 Editor：

```powershell
$editor = 'C:/Program Files/Unity/Hub/Editor/6000.3.13f1/Editor/Unity.exe'
$project = (Resolve-Path './unity_project').Path
& $editor -batchmode -job-worker-count 2 -projectPath $project `
  -executeMethod GGFramework.Demo.Editor.ShowcaseLifecycleTools.RunWithoutDomainReload `
  -logFile "$project/Logs/lifecycle.log"
```

Windows Player 先使用 **Build Windows Showcase** 构建。复现本次无图形生命周期：

```powershell
& "$project/output/showcase/GGFrameworkDemo.exe" -batchmode -nographics `
  --showcase-lifecycle --showcase-output "$project/Logs/player-lifecycle" `
  -logFile "$project/Logs/player-lifecycle.log"
```

源码与命令入口见[修复后操作指南](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/documents/showcase-guide.md#生命周期与重复播放回归)。集成回归实现为 [ShowcaseLifecycleChecks.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseLifecycleChecks.cs)；网络模块的逐项证据见[162 项测试结果](https://github.com/gonglei007/GGFramework-GGNetwork/blob/7e371eab8b9de00f06e713ca7bd8468ebb890ea0/documents/unity-verification-2026-11-20.json)。

各独立模块分别以自己的项目为 `-projectPath`，执行 `-runTests -testPlatform EditMode -testResults <绝对 XML 路径>`；GGUser 的 PlayMode 另外执行，不能拿 EditMode 的结果代替。核对进程退出码、XML 和文本报告三者，不以日志中的弱指针清理提示作为无泄漏证明。

## 未覆盖项

- Editor 日志还出现 Unity Search 索引的 `ArgumentOutOfRangeException`。生命周期捕获器排除堆栈含 `UnityEditor.Search` 的 Editor 索引错误，并单独允许故意注入的 Lua 语法错误；其他运行时 Error / Exception / Assert 仍会使回归失败。索引异常保留在原始日志，未修改 Unity Editor 本身，也不以游戏断言通过宣称 Editor 全程没有错误。
- 操作是调用页面背后的真实 API，未逐项进行鼠标点击、键盘输入、布局、NGUI 动画或 UGUI 后端视觉验收。
- 资源断言涵盖专属运行时 TextAsset、缓存计数、存活实例和示例 Bundle 数量；没有使用 Memory Profiler 证明全部 CPU / GPU 内存无泄漏，也没有验证多个业务拥有者共享同名缓存时的释放安全。
- 迟到任务 / 协程结果验证旧拥有者不再更新，不证明后台计算已经被强制取消；未穷尽资源加载、HTTP Abort 与完成的所有竞态。
- 未覆盖移动真机、IL2CPP、WebGL、其他 Unity 版本、远程资源来源与补丁签名 / 下载 / 回滚。
- 模拟 SDK 不验证真实认证、渠道沙箱、服务端票据校验、持久化交易账本和退款对账；独立网络单元测试不代替真实 HTTPDNS / WebSocket / Pomelo 服务联调。
- 知识库 GitHub CI 检查文档、示例和浏览器回归，不会执行这些外部 Unity 工程。实际 Unity 结果来自本记录中的本机运行。

继续阅读：[Core](GGFrameworkCore基础能力实践.md) · [资源](GGFramework资源管理实践.md) · [网络](GGFramework客户端网络实践.md) · [UI](GGFrameworkUI管理实践.md) · [用户与 SDK](GGFramework用户与SDK接入实践.md) · [Lua](GGFrameworkLua与热更新实践.md)。
