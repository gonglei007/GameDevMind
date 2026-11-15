# 文档质量与内容生成工具

本地与 CI 共用检查脚本。内部链接与生成工具只依赖 Python 3.11 标准库；文档检查配置见 [tools/config.yaml](../config.yaml)。

## 内容来源与统计口径

- `mds/` 文件与正文的标题、标签是内容清单来源，新增正文会自动纳入。
- [content_catalog.py](content_catalog.py) 中的 `PARENT_OVERRIDES` 只记录逻辑归属与历史编号不同的节点，保持旧路径稳定。
- [推荐阅读路径](../../mds/topics/推荐阅读路径.md) 是三条路径的清单来源，导航只提取其中的核心文档。
- 总文档数：`mds/` 下全部 Markdown；核心文档：六大能力域内文档，含目录页；其余为专题与说明。
- 代码集合数统计 `code/*/README.md`；案例与 AI 对话统计对应目录中除 README 外的 Markdown。

## 修改正文后

```bash
python tools/check/generate_catalog.py
```

统一更新：`INDEX.md`、`KEYWORDS.md`、`nav/content-data.js`、六个模块首页目录、README 统计与阅读路径篇数。两个导航页共用 `content-data.js`，不再各自维护 DOCS 数组。生成结果不包含运行时间，重复执行不会产生无意义差异。正文和 README 的生成区块之外仍可手工编辑。

## 提交前验证

```bash
python -m unittest discover -s tools/check -p 'test_*.py' -v
python tools/check/check_docs.py
python tools/check/check_links.py
python tools/check/check_images.py
python tools/check/generate_catalog.py --check
node --test tools/check/test_navigation_urls.cjs
node --test tools/check/test_navigation_interactions.cjs
node --test tools/check/test_navigation_controls.cjs
```

- `check_docs.py`：UTF-8、叶子文档必填字段；缺图返回非零；展示格式问题仍为告警。
- `check_links.py`：离线检查内部文件、目录、Markdown 标题锚点及 HTML ID。覆盖根目录 Markdown，以及 `mds/`、`cases/`、`ai-cases/`、`code/`、`docs/`、`tools/`、`nav/`、`.github/` 的 Markdown/HTML；排除构建产物和依赖目录。代码围栏、行内代码、HTML 注释、脚本正文中的示例不作为链接。
- `check_images.py`：检查 Markdown 图片、HTML 图片及指向图片的普通链接；缺失图片阻断，未引用和大文件只报告，不自动删除或压缩。
- `generate_catalog.py --check`：只读验证生成结果；缺失或过期时返回非零，并提示重新生成。
- `test_navigation_urls.cjs`：使用 Node.js 22 内置测试模块，验证 GitHub Pages 上正文进入 GitHub 排版视图、代码目录进入 tree 视图，以及离线/本地导航的相对路径和 `C#` 等特殊文件名。在线阅读不依赖 Pages 直接渲染 `.md` 文件。
- `test_navigation_interactions.cjs`：以可控计时验证全景节点单击延迟折叠、双击取消折叠并只打开一次，以及视图重绘时取消待处理点击；避免第一次点击重建 DOM 后吞掉双击。
- `test_navigation_controls.cjs`：执行导航页实际脚本，验证搜索去除首尾空格、组合筛选、六个模块折叠后保留筛选、切换模块取消待处理点击，以及触屏拖动防误触、移动双指缩放锚点、单指续拖和居中缩放。使用最小 DOM 适配器验证状态与计算，不代替真实浏览器的布局和触屏实测。
- 同一控件回归还验证分类/学习路径重绘后保留焦点、节点键盘激活不受触屏误触标记影响、方向键和 Home/End 遍历当前模块，以及快捷键忽略 Ctrl/Meta/Alt、输入框、可编辑内容、输入法组合和已处理的事件。实际 Tab 顺序、Enter/空格的浏览器默认行为、焦点环、滚动后可见性和键盘打开文档由 Playwright 另行验证。
- [浏览器回归](browser/README.md)：Playwright Test 自动运行 README 的 GitHub 展示，以及当前 checkout 的搜索筛选、全景、手机触屏和键盘操作；失败保留截图、trace、视频与报告，已纳入 CI。
- 外部 URL 不在离线门禁范围内，需另行验证网络可达性。
- `template/` 是创作模板，`tmp/`、`.cursor/` 是工作资料，不作为发布内容扫描。

带 `#` 的文件名必须写成 `%23`（如 `C%23语言.md`）；路径编码与锚点用 `#` 分隔后，检查器才会正确定位。

[generate_keywords.py](generate_keywords.py) 仍可单独生成关键词索引，但提交前应运行统一生成命令。

## 导航键盘操作

- 两页都可以用 Tab / Shift+Tab 切换控件，Enter / 空格操作筛选按钮；分类和学习路径更新结果后保留按钮焦点。
- 全景节点采用一个 Tab 入口；↑/↓ 按当前可见节点移动，Home/End 到首尾节点；→ 展开或进入第一个子节点，← 折叠或返回父节点；Enter/空格切换展开状态。
- 从节点按 Tab 可到“打开文档”，Enter 在新页阅读，再按 Tab 可操作展开/折叠及缩放控件；Shift+Tab 可以返回节点。带焦点节点会移入可见区域，避开底部操作面板。
- 全景的 `+` / `=`、`-` 缩放，`0` / `R` 重置；浏览器组合键和编辑输入不触发全景快捷键。

## 案例回归

[循环引用案例](../../cases/memory-leak-slg.md) 有独立 C++17 生命周期验证程序。CI 在 Ubuntu 下启用 AddressSanitizer、LeakSanitizer 与 UndefinedBehaviorSanitizer；使用 CMake 时也可在示例目录构建后执行 `ctest --test-dir build --output-on-failure`。

[网络同步示例](../../code/gamedevmind/2.技术能力/2.2.1.网络与通信/network_sync/README.md) 还会逐帧比较确定性状态，验证输入确认、过期快照与停止输入后的预测收敛；CI 同样通过 CTest 和 sanitizers 运行。示例通过不代表真实弱网与容量指标已达标。

[客户端只读渲染审计](../../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/README.md) 的 .NET 10 核心回归已纳入 CI，验证引用身份、候选过滤、排序和快照隔离。Unity 2022.3 编译与场景只读集成回归在本地独立项目执行；这些正确性检查不代表 URP 真机提速已达标。

## CI 门禁

[数据库示例](../../code/gamedevmind/2.技术能力/2.2.2.数据库/README.md) 的 SQLite 回归在 Windows/Linux 执行；MySQL 事务契约以独立 InnoDB 和 Go race 验证。缺少真实服务配置时，CI 必须失败；备份恢复、复制与容量不在该正确性门禁中。

[服务端优化回归](../../code/gamedevmind/3.研发能力/3.2.3.服务端优化/README.md) 包含 Go 快照并发/真实 MySQL-Redis 集成，以及 C++17 锁序夹具。Go race 检查与依赖集成在独立 CI 服务中运行，C++ 启用 ASan/UBSan 和 timeout；失败阻断，但不代表产品容量、故障切换或长期无死锁。

- [check-links.yml](../../.github/workflows/check-links.yml)：内部链接与锚点。
- [format-check.yml](../../.github/workflows/format-check.yml)：检查器回归、文档与图片、案例回归。
- [generate-index.yml](../../.github/workflows/generate-index.yml)：生成一致性。
- [browser-regression.yml](../../.github/workflows/browser-regression.yml)：真实浏览器交互与 GitHub README 展示。

上述失败均返回非零，不使用忽略错误继续通过的配置。main 已启用 17 项必需检查与管理员约束，内容更新必须通过 PR；完整清单、正反向验证和维护流程见 [CI 门禁与 main 分支维护](../../.github/CI_MAINTENANCE.md)。

## README 最近提交维护

[update_readme_pr.py](update_readme_pr.py) 供 [update-readme.yml](../../.github/workflows/update-readme.yml) 每小时及手动执行，默认本地仅预览，工作流通过 `--apply` 写入固定的 `codex/auto-readme-updates` 分支。

```bash
python tools/check/update_readme_pr.py
python -m unittest discover -s tools/check -p test_readme_pr.py -v
```

- 仅维护 README 中一对 `<!-- COMMIT-START -->` / `<!-- COMMIT-END -->` 标记之间的区块。当前首页没有这对标记，因此正常执行会报告无变化，不重新添加首页区块，也不创建 PR。若将来需要启用此区块，应先通过普通 PR 加入成对标记；单边、重复或反向标记直接报错。
- 从最新 `origin/main` 读取 README 和最后五条有效非合并提交，不使用本地工作区内容；忽略本自动化和旧版机器人生成的最近提交更新，避免合并更新 PR 后无限产生自我更新。生成无时间戳，转义提交标题，保留区块外文本与换行。
- main 内容无变化时不提交、不创建新 PR，也不主动关闭现有 PR。有变化时只使用固定更新分支，已有开放 PR 则复用；同一目标内容和 head 不重复创建提交、PR 或 CI 调度。
- main 更新后重新以最新 main 的树生成内容，旧更新 head 和最新 main 都作为父提交；仅快进更新固定分支，不强推、不丢弃分支历史。若发现该分支有其他文件或生成区块外的人工修改，报错并保留现场；准备更新时 main 已变化也报错，下一轮从最新 main 重试。
- 工作流并发组固定且不取消正在运行的任务。失败不会被当作“无变化”；API 部分失败后可复用已写入的 head/PR，只补调度该 head 缺失的工作流，已失败的 CI 不会每小时自动反复重跑。

机器人 PR 仍遵守 main 的 17 项必需检查。[GitHub 的工作流触发规则](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow)规定，`GITHUB_TOKEN` 产生的 PR 运行可能需要人工批准，不能假设会自动无人值守完成；`workflow_dispatch` 是可直接触发运行的例外。因此脚本主动向更新分支调度 `check-links.yml`、`format-check.yml`、`generate-index.yml`、`browser-regression.yml`，产生当前 head 对应的全部检查，不伪造成功状态，也不自动审批或合并 PR。

仅更新任务具有 `contents: write`、`pull-requests: write`、`actions: write`，checkout 不持久化凭据，不需要另存 PAT 或管理员令牌。仓库 Actions 设置需允许 GitHub Actions 创建 PR；权限不足时会明确失败，不降级为直推或绕过。

[test_readme_pr.py](test_readme_pr.py) 已随现有 `Check Markdown Format` 必需任务执行，覆盖无变化、标记异常、标题转义/换行、真实 Git 日志去除机器人反馈、创建与复用 PR、main 前进、拒绝人工修改、CI 部分调度恢复和工作流权限契约。GitHub 写操作由 API 边界夹具验证；当前无标记路径另可在合并后手动执行工作流，核对真实无变化退出。
