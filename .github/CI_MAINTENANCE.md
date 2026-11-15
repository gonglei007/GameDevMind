# CI 门禁与 main 分支维护

本页记录 main 的线上保护配置、必需检查及验收证据，作为后续 PR 维护依据。配置核对日期：2026-11-15；实际生效状态以 [GitHub 分支保护设置](https://github.com/gonglei007/GameDevMind/settings/branches) 和 API 回读为准。工作流及测试范围见 [GitHub Actions 工作流说明](workflows/README.md)。

## main 分支保护

当前使用精确匹配 `main` 的分支保护规则：

| 项目 | 配置 |
|---|---|
| 更新入口 | 必须通过 Pull Request 更新 main |
| 必需检查 | 下表 17 项，全部绑定 `github-actions`（GitHub App ID `15368`） |
| 分支最新要求 | 开启，`required_status_checks.strict = true` |
| 管理员约束 | 开启，`enforce_admins.enabled = true`；管理员同样受门禁约束 |
| PR 人工审批数 | `0`；要求 PR，但不额外强制他人审批 |
| PR 绕过名单 | 无用户、团队或 App 绕过名单 |
| 强制推送 / 删除 main | 均禁止 |

CI 失败、必需检查未产生或仍在运行时不能合并；分支落后于 main 时需更新分支并重新验证。不要直推 main、使用 `--admin` 合并，或临时关闭保护以完成普通内容更新。自动维护脚本同样遵守 PR 流程。

[GitHub 对必需状态的定义](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)也接受 `neutral` / `skipped` 的检查结论，因此本仓库的必需任务应保持在 PR 中实际运行，不使用条件跳过或 `continue-on-error` 替代验证。下述正向验收逐项核对了 17 个 `completed / success`，没有用跳过状态充数。

## 17 项必需检查

使用实际 check-run 的完整名称，不使用工作流标题或 job ID。Windows/Linux 矩阵展开后分别计数，名称必须唯一。

| 序号 | 必需检查名称 | 来源工作流 |
|---|---|---|
| 1 | `Check Internal Links` | [check-links.yml](workflows/check-links.yml) |
| 2 | `Check Navigation Indexes and Statistics` | [generate-index.yml](workflows/generate-index.yml) |
| 3 | `Check Markdown Format` | [format-check.yml](workflows/format-check.yml) |
| 4 | `Check Guild Ownership Case` | [format-check.yml](workflows/format-check.yml) |
| 5 | `Check Network Synchronization Examples` | [format-check.yml](workflows/format-check.yml) |
| 6 | `Check Network Protocol and Sockets (ubuntu-latest)` | [format-check.yml](workflows/format-check.yml) |
| 7 | `Check Network Protocol and Sockets (windows-latest)` | [format-check.yml](workflows/format-check.yml) |
| 8 | `Check Client Render Audit` | [format-check.yml](workflows/format-check.yml) |
| 9 | `Check Client Network Lifecycle (ubuntu-latest)` | [format-check.yml](workflows/format-check.yml) |
| 10 | `Check Client Network Lifecycle (windows-latest)` | [format-check.yml](workflows/format-check.yml) |
| 11 | `Check Server Leaderboard Snapshot` | [format-check.yml](workflows/format-check.yml) |
| 12 | `Check Server Lock Order` | [format-check.yml](workflows/format-check.yml) |
| 13 | `Check SQLite Database Example (ubuntu-latest)` | [format-check.yml](workflows/format-check.yml) |
| 14 | `Check SQLite Database Example (windows-latest)` | [format-check.yml](workflows/format-check.yml) |
| 15 | `Check MySQL Transaction Contracts` | [format-check.yml](workflows/format-check.yml) |
| 16 | `Check Navigation Browser Regression` | [browser-regression.yml](workflows/browser-regression.yml) |
| 17 | `Check GitHub README Browser Regression` | [browser-regression.yml](workflows/browser-regression.yml) |

这四个工作流都在面向 main 的 PR 中运行。Pages 的 `build`、`deploy`、`report-build-status` 属于合并后发布检查，不加入上述 PR 必需清单，否则 PR 可能永久等待未触发的任务。main 上通常看到的 20 项检查，是这 17 项再加 3 项 Pages 检查。

定时/手动的 [update-readme.yml](workflows/update-readme.yml) 不属于 PR 门禁。它保留了历史直推逻辑；若需要让它实际写入 main，应先改为创建 PR，不能为机器人添加绕过权限。

## 正反向实测记录

两次测试均于 2026-11-15 完成，基线 main 为 `ca667be86528987e10b32a3e8b400b8d708ae0d7`；均为非草稿 PR、分支与 main 同步、无代码冲突，也无人工审批要求阻塞。

| 验证 | 测试内容与 CI | GitHub 合并门禁 | 清理结果 |
|---|---|---|---|
| 反向：[PR #25](https://github.com/gonglei007/GameDevMind/pull/25) | 仅新增临时 Markdown 断链；`Check Internal Links` 返回 exit code 1，其余 16 项成功。[失败日志](https://github.com/gonglei007/GameDevMind/actions/runs/43672266860) | REST：`mergeable = true`、`mergeable_state = blocked`；GraphQL：`MERGEABLE / BLOCKED`、`reviewDecision = null` | 已关闭、未合并；临时分支已删除 |
| 正向：[PR #26](https://github.com/gonglei007/GameDevMind/pull/26) | 仅新增含有效内部链接的临时说明；17 项必需检查均为 `completed / success`。[浏览器检查](https://github.com/gonglei007/GameDevMind/actions/runs/43672779903) | REST：`mergeable = true`、`mergeable_state = clean`；GraphQL：`MERGEABLE / CLEAN` | 已关闭、未合并；临时分支已删除 |

`MERGEABLE` 只说明无代码冲突，不能单独作为合并许可；正反向测试同时读取了 `mergeStateStatus`。失败时为 `BLOCKED`，全部通过后为 `CLEAN`。

两条测试提交及测试文件均未进入 main，保护规则未被放宽。正向测试收尾时，独立的 [PR #27](https://github.com/gonglei007/GameDevMind/pull/27) 将 main 更新至 `925ea6e2a8f2bbeef7568a5e16eb70724225526e`；这是另外一条正常内容 PR，不是测试 PR 的合并。两条测试 PR 的描述中保留了核对结果。

## 后续通过 PR 更新 main

1. **从最新远端分支开始。** 保留已有工作区改动，获取 `origin/main`，使用 `codex/` 前缀创建任务分支，不在 main 上提交待发布改动。

   ```bash
   git fetch origin
   git switch -c codex/<topic> origin/main
   ```

2. **修改并在本地验证。** 按改动运行 [内容检查](../tools/check/README.md#提交前验证) 和必要的 [浏览器回归](../tools/check/browser/README.md#本地运行)。正文或导航来源改变时先重新生成目录，再检查统计一致性。只暂存本次任务文件。

3. **推送任务分支，创建面向 main 的 PR。** PR 描述说明最终改动和验证结果；多行正文使用文件，保留实际换行。

   ```bash
   git push -u origin codex/<topic>
   gh pr create --base main --head codex/<topic> --body-file <pr-body-file>
   ```

4. **等待全部必需检查。** 用 PR 最新 head SHA 核对 17 项名称、GitHub Actions 来源和成功结论，不能只看某一个工作流。失败就修复并推送到同一分支；缺失就检查工作流触发条件、job 更名和矩阵。只有明确的基础设施故障才重跑，不以反复重跑掩盖真实错误。

   ```bash
   gh pr checks <PR> --required --watch --fail-fast
   gh pr view <PR> --json headRefOid,isDraft,mergeStateStatus,reviewDecision
   ```

   如果显示 `BEHIND`，先在任务分支执行 `git fetch origin`、`git merge origin/main`，解决冲突后验证并推送，重新等待最新提交的全部检查。任何新增提交都会使上一轮验收不足以作为当前 head 的合并依据。

5. **核对并合并当前已验证提交。** 非草稿、无冲突、分支最新、17 项成功且门禁为 `CLEAN` 后，才执行普通合并；使用 `--match-head-commit` 防止检查后 head 又被更新。遵守会话或项目要求的合并授权，不使用 `--admin` 绕过门禁。

   ```bash
   gh pr merge <PR> --merge --match-head-commit <verified-head-SHA> --delete-branch
   ```

6. **验证合并与发布。** 回读 PR 的 `mergedAt` / `mergeCommit`，更新本地 main 并核对远端提交；再检查合并提交上的 CI 和 Pages 发布。确认任务提交已进入 main 后清理已合并分支，不覆盖其他人的并行提交。

## 保护配置的维护与核对

以下命令只读，不修改规则：

```bash
gh api repos/gonglei007/GameDevMind/branches/main/protection
gh pr checks <PR> --required
gh api repos/gonglei007/GameDevMind/commits/<head-SHA>/check-runs
```

核对 `required_status_checks.checks` 的完整名称和 `app_id`，以及 strict、管理员约束、PR 要求、绕过名单、强推/删除开关。检查状态要对应最新 head；GitHub 的合并门禁还可能使用 PR 的测试合并提交，应结合 PR 检查页判断。

新增检查、重命名 job 或调整系统矩阵时，同步维护本页和线上必需清单。迁移期间先确保新旧检查可同时产出，验证新名称后再调整保护；不要先删旧任务，留下永远处于 `Expected` 的必需名称。取消验证、启用跳过或放宽管理员约束不能当作修复 CI 的办法。
