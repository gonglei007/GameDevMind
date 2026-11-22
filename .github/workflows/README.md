# GitHub Actions 工作流说明

main 的实际保护配置、17 项必需检查、正反向验收证据和 PR 更新流程统一见 [CI 门禁与 main 分支维护](../CI_MAINTENANCE.md)。

## 必须通过的检查

所有检查均在 main 的 Push、Pull Request 和手动触发时执行，只需 `contents: read` 权限。

- [check-links.yml](check-links.yml)：离线验证发布内容的内部文件、图片链接与标题锚点。外链网络可达性不在此门禁范围内。
- [format-check.yml](format-check.yml)：检查器单元测试、正文必填字段、图片引用；另以 C++17 和 sanitizers 执行循环引用案例与网络同步回归，使用 .NET 10 执行客户端只读渲染审计的引用身份、候选过滤和快照回归。
- [generate-index.yml](generate-index.yml)：验证两个导航页共用的数据、模块目录、文档索引、关键词索引与统计是否和正文一致。
- [browser-regression.yml](browser-regression.yml)：以锁定版本的 Playwright/Chromium 执行当前 checkout 的导航、全景、手机触屏、键盘回归，并检查提交 SHA 对应的 GitHub README 展示；main push 另查公共首页。

内部链接、缺图和生成漂移均使检查失败；大图片与未引用资源只报告。上述四个工作流的 17 项 PR 检查已设为 main 的必需检查，管理员同样受约束；更新 main 必须走 PR。

正文格式任务另以 Node.js 22 内置测试检查导航 URL：GitHub Pages 的文档和代码入口必须进入 GitHub 的 blob/tree 视图，离线与本地相对路径保持可用，并验证特殊文件名编码。页面展开、图片加载与真实跳转仍通过浏览器实测，不由此 URL 回归替代。

同一任务以可控计时核对全景图的单击/双击互斥与取消，防止父节点先折叠重绘、再丢失双击跳转。浏览器另实测真实父节点双击和单击折叠/展开。

导航控件回归还执行页面实际脚本，核对搜索空格、组合筛选、六模块折叠后保留筛选、触屏拖动防误触、双指缩放锚点、单指续拖及缩放中心。此门禁用最小 DOM 适配器检查状态与坐标计算；手机布局、触摸命中和文档按钮仍以 Playwright 触屏浏览器验证。

同一回归覆盖分类/学习路径重绘后的焦点保留、节点键盘激活与方向键/Home/End 移动，以及快捷键对组合键、编辑目标、输入法和已处理事件的隔离。真实 Tab/Shift+Tab 顺序、Enter/空格、焦点环及窄屏遮挡由 Playwright 浏览器验证。

浏览器工作流有 **Check Navigation Browser Regression** 和 **Check GitHub README Browser Regression** 两个独立检查，失败均阻断任务，不依赖 Pages 发布顺序。导航对当前 checkout 启动本地只读服务；README 访问实际 GitHub 的不可变 SHA 页面，PR 不误测旧 main。配图加载、折叠、重点入口、三种手机视口、原生触摸手势、焦点与快捷键都执行断言。第三方徽章只保留入口与加载诊断；仓库配图加载是硬断言。

两个检查无条件保留非取消任务已生成的报告产物，包括失败截图、trace 和视频，保留 7 天；网络故障不会被降级成通过。本地命令、范围和 Chromium/触屏模拟的边界见 [浏览器回归说明](../../tools/check/browser/README.md)。

客户端审计 CI 只运行不依赖 Unity 的核心；实际 Unity 2022.3 编译与只读场景回归在本地 Editor 中运行，命令见 [render_audit](../../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/README.md)。两者都不能代替目标机 URP 性能验收。

服务端优化增加 **Check Server Leaderboard Snapshot**（Go race + 独立 MySQL 8.0/Redis 7.4）和 **Check Server Lock Order**（C++17 + ASan/UBSan + 外部超时）。真实依赖配置缺失、竞态、快照/锁序回归均阻断；不使用生产数据，不把正确性测试当作容量或长期稳定性报告。命令与边界见 [服务端优化示例](../../code/gamedevmind/3.研发能力/3.2.3.服务端优化/README.md)。

数据库增加 **Check SQLite Database Example**（Windows/Linux 的迁移、CAS、奖励和排行榜）及 **Check MySQL Transaction Contracts**（真实 InnoDB 的原子效果、幂等身份、回滚和 RC/RR 读视图，含 Go race）。MySQL 必须配置独立服务，缺失不允许跳过；SQLite 不替代其他引擎。运行范围见 [数据库示例](../../code/gamedevmind/2.技术能力/2.2.2.数据库/README.md)，不包含生产容量和备份恢复验收。

客户端网络系统增加 **Check Client Network Lifecycle**（Windows/Linux，Python 标准库）：阻断验证认证/恢复门禁、旧代次、一次终态、取消/超时/关闭、重试预算与真实工作线程邮箱；同时验证持续服务器的延迟通道、输入排空和远端插值模型。命令与边界见 [生命周期模型](../../code/gamedevmind/3.研发能力/3.1.4.客户端网络系统/client_network/) 和 [延迟同步模型](../../code/artile-sample-code/03-rd/03-sync/)。这些不是 Unity、DNS/TLS、切网、强更完整流程或业务幂等验收。

网络与通信增加 **Check Network Protocol and Sockets**（Windows/Linux，Python 标准库）。协议类型、长度分帧、部分写入/背压、时间心跳和输入确认模型，以及真实本机 TCP/UDP 回环均为阻断断言。临时端口与超时避免固定端口冲突和无限等待；不包含公网弱网、TLS、RPC、消息队列、容量或引擎物理验收。命令见 [协议示例](../../code/artile-sample-code/02-technical/05-networking/) 和 [Socket 示例](../../code/artile-sample-code/01-foundation/06-os-network/)。

## 更新索引与导航

正文标题、标签、文件列表和阅读路径是内容来源。修改后在本地运行：

```bash
python tools/check/generate_catalog.py
python tools/check/generate_catalog.py --check
```

生成脚本只更新指定生成区块，不覆盖其余手工内容。`generate-index.yml` 现在执行只读一致性检查，不再在 main 上自动提交文件；过期输出应与正文一起在 PR 中审查。

完整范围、统计口径和验证命令见 [tools/check/README.md](../../tools/check/README.md)。

## 外部 GGFramework Unity 回归

GGFramework Demo、Core、GGResource、GGNetwork、GGUI、GGUser 在各自仓库执行真实 Unity 6000.3.13f1 回归，包含 Demo 两轮播放/退出、资源释放与 Windows Mono Player，以及模块自己的测试契约。触发、一次性授权 runner、artifact 和未覆盖范围统一见 [GGFramework 自动化回归与 CI 复现](../../docs/工程实践/GGFramework自动化回归与CI.md)。这些外部工作流不替代本知识库的文档/浏览器检查，也不加入这里的 17 项必需检查清单。

## 其他维护流程

[update-readme.yml](update-readme.yml) 每小时或手动检查 README 的可选最近提交区块，有变化时创建或复用固定更新 PR，不直推 main；无标记或无差异时不创建 PR。通过显式 `workflow_dispatch` 调度四个现有 CI 工作流，仍需通过 17 项必需检查后普通合并。只在该任务授予 contents、pull-requests、actions 写权限，不为机器人添加分支保护绕过。完整行为与本地验证见 [README 最近提交维护](../../tools/check/README.md#readme-最近提交维护)。正文统计由统一内容生成工具负责。
