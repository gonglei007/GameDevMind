# 只读渲染引用审计

对应 [客户端优化](../../../../../mds/3.研发能力/3.1.3.客户端优化.md) 和 [Draw Call 诊断案例](../../../../../cases/drawcall-optimization.md)。用于替代旧案例按 Shader/主纹理自动覆盖材质的危险脚本。

## 行为与边界

- `RenderAuditCore.cs`：不依赖 Unity，输入同一次场景快照，统计材质对象身份和状态，排序后输出共享 Mesh/Material 的候选。
- `Editor/RenderAuditEditor.cs`：针对 Unity 2022.3，读取已加载的普通场景（包括 additive），排除 preview/Prefab Stage，包含 inactive/disabled 对象用于清点。仅访问 MeshRenderer、MeshFilter.sharedMesh、sharedMaterials 和 HasPropertyBlock，不调用会创建材质副本的 materials/material getter。
- 候选仅包含启用且 activeInHierarchy、无 MPB、单子网格、恰好一个非空材质槽的对象。同名材质、同 Shader/主纹理不能当成同一个 Material；运行时 ID 只能在当前会话快照内比较。
- 多子网格、空材质、空 Mesh、MPB 等保守排除，不代表这些对象永远不能优化。各排除计数可以重叠。
- 工具不判断 Shader/管线、灯光、阴影、Lightmap、变体与空间可见性，不承诺实际合批或性能收益；用 Frame Debugger 和目标机记录进一步核实。
- 审计不写文件，不修改 sharedMaterials、Static、MPB 或场景。集成测试会在独立临时项目创建测试资源，不能放入生产工程自动执行。

## 使用审计工具

将 `RenderAuditCore.cs` 和 `Editor/RenderAuditEditor.cs` 分别放进项目的 `Assets/RenderAudit/` 与其 `Editor/` 子目录。不要将回归测试脚本复制进生产项目。Unity 编译后运行 **Tools → GameDevMind → Read-only Render Audit**，报告输出到 Console。先只读核对清单，再另行设计带预览、Undo、持久化和回滚的资源修改。

## 核心回归（无需 Unity）

要求 .NET 10 SDK，不依赖第三方 NuGet 包。从仓库根目录执行：

```bash
dotnet run --project 'code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/RenderAudit.Regression.csproj' --configuration Release
```

失败返回非零。覆盖相同引用/不同身份、不同 Mesh、MPB、inactive、缺 Mesh、空槽、多槽、多子网格、输入乱序、快照隔离与空输入。此项目与 Unity 共用同一核心源码，以 C# 9 语法编译；.NET 目标版本不代表 Unity 运行时版本。

CI 的 **Check Client Render Audit** 执行此回归。它不编译 Editor 适配器；Editor API 正确性由下面的实际 Unity 回归单独验证。

## Unity Editor 集成回归

用安装并已激活的 Unity 2022.3，在仓库忽略目录下新建一次性空项目。以下 PowerShell 命令从仓库根目录执行，修改 Editor 路径以匹配本机安装；不要使用现有游戏项目：

```powershell
$auditSource = (Resolve-Path 'code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit').Path
$auditProject = Join-Path (Get-Location) ('output/validation/render-audit-' + [guid]::NewGuid().ToString('N'))
$auditEditor = 'C:\Program Files\Unity 2022.3.62f3\Editor\Unity.exe'
New-Item -ItemType Directory -Force "$auditProject/Assets/Editor", "$auditProject/Packages", "$auditProject/ProjectSettings" | Out-Null
[IO.File]::WriteAllText("$auditProject/Packages/manifest.json", '{"dependencies":{}}', [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText("$auditProject/ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 2022.3.62f3`n", [Text.UTF8Encoding]::new($false))
Copy-Item "$auditSource/RenderAuditCore.cs" "$auditProject/Assets/"
Copy-Item "$auditSource/Tests/CoreRegression.cs" "$auditProject/Assets/Editor/"
Copy-Item "$auditSource/Editor/*.cs" "$auditProject/Assets/Editor/"
$auditArgs = @('-batchmode', '-nographics', '-noUpm', '-projectPath', "`"$auditProject`"", '-executeMethod', 'GameDevMind.ClientOptimization.UnityRegression.Run', '-logFile', "`"$auditProject/regression.log`"")
$auditProcess = Start-Process -FilePath $auditEditor -ArgumentList $auditArgs -WindowStyle Hidden -PassThru -Wait
if ($auditProcess.ExitCode -ne 0) { throw "Unity regression failed; inspect $auditProject/regression.log" }
if (-not (Select-String -Path "$auditProject/regression.log" -SimpleMatch 'PASS: Unity render audit')) { throw 'Unity success marker missing' }
```

ProjectVersion 中版本号应与所选 Editor 匹配；`-noUpm` 禁用包管理器，避免空项目初始化下载无关模板包。本例不使用外部包，参数含义见 [Unity 命令行文档](https://docs.unity3d.com/cn/2022.3/Manual/EditorCommandLineArguments.html)。测试入口主动以 0/1 退出；编译或许可证问题也必须检查日志，不得把进程启动成功当测试通过。测试创建同名同 Shader、主纹理相同但颜色不同的材质，以及共享引用、MPB、inactive、disabled、缺 Mesh、空/多槽、additive 和 preview 场景，检查：

1. 只列出共享引用候选，不把不同材质误合并；状态与范围正确。
2. 菜单入口与直接采集都不改写材质、MPB、Static、序列化状态或 clean scene 的 dirty 状态。
3. 非普通场景被拒绝；核心回归也在 Unity C# 编译环境执行。

该测试使用内置 Unlit/Color 构造夹具，不安装 URP，不渲染目标游戏，也不测试 GPU 实例化是否生效。它证明工具的读取行为，不是性能基准。真机预算、画面对照和热稳态测试见 [客户端优化：验证方法](../../../../../mds/3.研发能力/3.1.3.客户端优化.md#验证方法)。

## 本次复核记录

2026-10-16：Windows 下 .NET 10.0.401 核心回归通过；Unity 2022.3.62f3 在全新一次性项目中实际编译并执行上述入口，退出码 0，成功标记为 `PASS: Unity render audit references, MPB, static flags, inactive objects and clean scenes`。文档、内部链接、图片与生成一致性检查也已通过。此记录未包含 URP 真机性能或画面验收。
