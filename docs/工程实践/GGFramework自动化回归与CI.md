# GGFramework 自动化回归与 CI 复现

本页把[首次 Unity 实跑记录](GGFrameworkUnity验证记录.md)中的操作与退出检查组织为可重复执行的 CI。环境仍为 Windows / Unity **6000.3.13f1**；Demo Player 为 Windows x64 Mono Development。阅读入口：[GGFramework 实践导读](GGFramework.md)。

## 六仓的执行契约

| 仓库 | 最低通过数量与实际范围 |
|---|---|
| Demo | 稳定 Core EditMode 66；Editor 冒烟 28；关闭 Domain Reload 的两个完整播放/退出周期各 35；3 个旧 Prefab 实际导入；Windows Mono Player 构建、冒烟 27、生命周期 35 |
| Core main 预览包 | 包外临时 Unity 宿主加载当前检出的包，EditMode 104；与 Demo 固定的稳定包分别测试 |
| GGResource | EditMode 15，PlayMode 2；最后持有释放和显式独占组清理后的缓存/原生对象销毁 |
| GGNetwork | EditMode 162；含可选 BestHTTP 缺失时的明确失败与诊断关闭，不替代真实服务联调 |
| GGUI | 现有 EditMode 11；不外推到完整页面栈、NGUI/UGUI 后端等价或动画视觉 |
| GGUser | EditMode 71、PlayMode 11；当前假渠道/网关及管理器生命周期 |

契约分别位于各仓 `ci/unity-regression.json`。共享执行器的唯一维护来源是 [Demo tools/ci](https://github.com/gonglei007/GGFramework-Demo/tree/6fba3a32aae1951df8dd034dd15f36a36ab25895/tools/ci)，其他模块工作流固定完整提交 SHA；不因此统一升级各模块的 Core 运行时依赖。

Demo 的退出断言包括：所属 UI 登记与页面栈移除、其他拥有者登记保留、原生 TextAsset 与专属缓存释放、池实例销毁、事件退订、迟到结果不能写回旧拥有者、回环监听关闭、同会话重开、两次实际退出及 Editor 设置恢复。阈值允许新增用例，但不能靠删掉关键断言维持数量。

## 本地完整复现

准备 PowerShell 7.2+、Python 3.10+、Git、已为当前 Windows 用户激活的 Unity 6000.3.13f1，Demo 还需对应 Windows Mono 构建支持与 ToLua 原生插件。导读手工体验所固定的旧提交不包含本轮 CI 脚本；请另建检出目录并固定已验证的 CI 提交，避免切换正在编辑的工程：

```powershell
git clone --no-checkout https://github.com/gonglei007/GGFramework-Demo.git GGFramework-Demo-CI
git -C GGFramework-Demo-CI checkout --detach 6fba3a32aae1951df8dd034dd15f36a36ab25895
Set-Location ./GGFramework-Demo-CI
```

从这个 Demo 仓库根运行：

```powershell
./tools/ci/Invoke-UnityRegression.ps1 -RepositoryRoot $PWD `
  -OutputRoot 'D:/ggframework-results/demo-new-run' `
  -PythonExecutable 'C:/Python312/python.exe'
```

将参数换为本机实际路径，输出目录必须尚不存在。对独立模块，按本页结果表的 PR 或合并后 SHA 另外检出对应仓库，把 RepositoryRoot 换为其仓库根，并使用工作流固定的共享脚本。Core 的输出必须放在包目录之外，避免把临时 Unity 工程递归导入包。

例如，保持当前目录为上面固定版本的 `GGFramework-Demo-CI`，验证独立 Core 预览包：

```powershell
git clone --no-checkout https://github.com/gonglei007/GGFramework-Core.git ../GGFramework-Core-CI
git -C ../GGFramework-Core-CI checkout --detach 0771bf57690a8af6f0bd1fe06ff6473e4a957fe7
./tools/ci/Invoke-UnityRegression.ps1 -RepositoryRoot ../GGFramework-Core-CI `
  -OutputRoot 'D:/ggframework-results/core-new-run' `
  -PythonExecutable 'C:/Python312/python.exe'
```

其余模块同样复用这个 Demo 检出中的脚本，替换模块仓库与完整 SHA；完整提交值保存在结果索引中。

执行器自动构建所需本地 Bundle，顺序运行各阶段。旧报告及旧构建入口先保全；只有新文件、成功退出码和完整证据才能通过。任一阶段超时、缺少报告、NUnit 空跑/跳过/失败、缺失退出证据或构建产物都会失败。连续 Editor 启动还会等待并收尾已经退出的本轮 Editor 所属 ILPP/UPM 子进程，不结束其他 Unity 工程。

## 触发真实 Actions

PR 的 `Validate PR CI Contract` 在 GitHub 托管 Ubuntu runner 上验证契约、报告门禁反向测试与 PowerShell 语法。分支 push 启动 `Validate Unity CI Contract` 和实际 `Unity Regression` job；拥有者也可手动触发已经在默认分支上的工作流。静态检查通过不代表 Unity 已运行。

本次按选定方案使用一次性 Windows runner：只有拥有者触发、明确完整 SHA 的受信任 push/dispatch 才交给工作站。fork PR 不直接运行工作站代码；其他作者提交先由拥有者审查后在可信分支推送或手动触发。没有 runner 时实际 job 会排队，不能记为通过。

```powershell
./tools/ci/Start-OneShotRunner.ps1 `
  -Repository gonglei007/GGFramework-Demo `
  -Commit '<本次 push 的完整 40 位 SHA>' `
  -RunnerRoot 'D:/ggframework-runner' `
  -SeedRepository '<同一仓库的已审查本地检出路径>' `
  -PythonExecutable 'C:/Python312/python.exe'
```

SeedRepository 可省略；需要时只复制已经提交的 Git 对象，不复制在制工作树或 Library。启动器核对 origin、SHA、触发者、工作流路径、run/attempt 与排队标签，校验官方下载的 runner SHA-256。Actions 仍检出精确远端提交并清理工作区。临时目录和 UPM 缓存随 RunnerRoot 放置，不改用户或系统级环境设置。

每个 runner 只执行一个 job，结束后注销注册，不安装常驻服务、不上传 Unity 许可证。合并后的 main/master 是新的 SHA，会触发新一轮 CI，需要再启动一次 runner；重跑的 attempt 也不同。持续无人值守执行应另行部署隔离且已授权的专用环境，不能直接把个人工作站改成运行任意公共 PR 的常驻 runner。

多仓启动时还需限制整机并发。本次环境在三个工程同时首次导入时出现实际内存压力，撤销未完成的尝试后按最多两个 Unity 任务接续执行；被取消的导入不记为测试通过。可用内存需覆盖导入峰值，而不只看启动前的空闲值。

本轮也遇到 GitHub API 连接中断。启动或等待命令因网络错误退出时，先回读 `gh run view` 和 `gh api repos/<owner>/<repo>/actions/runners`，区分未注册、仍在运行及已完成；不要为仍在执行的同一 job 重复注册 runner。连接错误本身不能判定 Unity 测试成功或失败。

## 读取证据与合并

公共 artifact 名为 `unity-regression-<SHA>`，保留 14 天。`results.json` 包含准确提交、Unity/OS 环境、阶段时间与退出码、逐项 NUnit 结果、集成断言、原始报告摘要和构建产物摘要；失败时有失败记录与筛选诊断。完整授权日志和原始 XML 不公开上传，私有临时目录可能在 job 结束后被 runner 清理。

```powershell
gh pr checks <PR号> -R gonglei007/GGFramework-Demo
gh run view <run-id> -R gonglei007/GGFramework-Demo
gh run download <run-id> -R gonglei007/GGFramework-Demo `
  -n unity-regression-<SHA> -D ./ci-evidence
```

合并前核对当前 PR 的最新头、未解决评论、所有检查与真实 Unity artifact；合并后对新 SHA 重复核对。本次不改变源仓原有分支保护策略，知识库自己的 17 项必需检查也保持原样；不要把维护流程中的核对等同于已新增分支保护必需项。

<!-- ggframework-ci-results:start -->
## 本次接入的实际 CI 结果

已按精确提交核对六仓 PR 与合并后默认分支的 **12 次真实 Unity 工作流**，全部成功；各阶段退出码为 0，NUnit 没有失败、跳过或未决用例。远程检出排查及三工程并行导入时取消的尝试均不计入成功。逐项结果从公共 artifact 保全到知识库，避免 14 天保留期届满后只剩口头数量。

| 仓库 / PR | PR 的实际 Unity CI | 合并后实际 Unity CI | 保全证据 |
|---|---|---|---|
| [GGFramework-Demo](https://github.com/gonglei007/GGFramework-Demo/pull/2) | [6fba3a3](https://github.com/gonglei007/GGFramework-Demo/actions/runs/44681176439) | [e40af98](https://github.com/gonglei007/GGFramework-Demo/actions/runs/44683712316) | [PR](验证记录/GGFramework-CI-2026-11-20/demo-pr.json) / [合并后](验证记录/GGFramework-CI-2026-11-20/demo-main.json) |
| [GGFramework-Core](https://github.com/gonglei007/GGFramework-Core/pull/1) | [0771bf5](https://github.com/gonglei007/GGFramework-Core/actions/runs/44681272702) | [74d10ec](https://github.com/gonglei007/GGFramework-Core/actions/runs/44682532919) | [PR](验证记录/GGFramework-CI-2026-11-20/core-pr.json) / [合并后](验证记录/GGFramework-CI-2026-11-20/core-main.json) |
| [GGFramework-GGResource](https://github.com/gonglei007/GGFramework-GGResource/pull/1) | [9091119](https://github.com/gonglei007/GGFramework-GGResource/actions/runs/44681284775) | [921f2a5](https://github.com/gonglei007/GGFramework-GGResource/actions/runs/44683732072) | [PR](验证记录/GGFramework-CI-2026-11-20/resource-pr.json) / [合并后](验证记录/GGFramework-CI-2026-11-20/resource-main.json) |
| [GGFramework-GGNetwork](https://github.com/gonglei007/GGFramework-GGNetwork/pull/3) | [22043a3](https://github.com/gonglei007/GGFramework-GGNetwork/actions/runs/44681297924) | [529eede](https://github.com/gonglei007/GGFramework-GGNetwork/actions/runs/44685493910) | [PR](验证记录/GGFramework-CI-2026-11-20/network-pr.json) / [合并后](验证记录/GGFramework-CI-2026-11-20/network-main.json) |
| [GGFramework-GGUI](https://github.com/gonglei007/GGFramework-GGUI/pull/1) | [ececc3f](https://github.com/gonglei007/GGFramework-GGUI/actions/runs/44681310841) | [0e4d664](https://github.com/gonglei007/GGFramework-GGUI/actions/runs/44687293948) | [PR](验证记录/GGFramework-CI-2026-11-20/ui-pr.json) / [合并后](验证记录/GGFramework-CI-2026-11-20/ui-main.json) |
| [GGFramework-GGUser](https://github.com/gonglei007/GGFramework-GGUser/pull/1) | [77c0a27](https://github.com/gonglei007/GGFramework-GGUser/actions/runs/44681321315) | [8416a9a](https://github.com/gonglei007/GGFramework-GGUser/actions/runs/44689187989) | [PR](验证记录/GGFramework-CI-2026-11-20/user-pr.json) / [合并后](验证记录/GGFramework-CI-2026-11-20/user-main.json) |

[完整索引与运行元数据](验证记录/GGFramework-CI-2026-11-20/index.json)记录准确 SHA、run ID、执行模式和各阶段数量。[完工核验](验证记录/GGFramework-CI-2026-11-20/completion-audit.json)回读六仓默认分支、PR / 合并后检查和 runner 注册，确认没有遗留在线/离线注册；没有安装 Windows 服务。

<!-- ggframework-ci-results:end -->

## 验证边界

这套 CI 验证固定环境下的真实 API、播放与退出路径，不逐项点击鼠标/键盘，不验收视觉、全量 CPU/GPU 无泄漏、共享同名资产多拥有者、所有在途请求竞态、移动/IL2CPP/WebGL、真实渠道验单或生产热更新。

资源 PlayMode 用例没有初始化 Loxodon。Demo 临时 VM、独立 GGUI 资源模型、独立 GGNetwork 单元测试分别保持原有范围；通过退出断言不等于底层后台计算被强制取消。更详细的实际失败与环境边界保留在[首次实跑记录](GGFrameworkUnity验证记录.md)。

继续阅读：[实践导读](GGFramework.md) · [资源管理](GGFramework资源管理实践.md) · [Core 基础能力](GGFrameworkCore基础能力实践.md)。
