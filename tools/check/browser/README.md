# 浏览器回归

把 README 与导航的实际浏览器检查固定为 CI 门禁。依赖单独维护在本目录，锁定 Playwright Test 与对应 Chromium，不影响其他工具的依赖。

## 本地运行

需要 Node.js 22+。从仓库根目录执行：

```bash
cd tools/check/browser
npm ci
npx playwright install chromium
npm run test:local
npm run test:readme
```

`npm test` 一次执行全部项目；`npm run report` 打开上一次 HTML 报告。Linux 首次安装可以使用 `npx playwright install --with-deps chromium`。临时服务器只监听 `127.0.0.1:4173`，由测试启动和关闭；已有服务占用端口时直接报错，不复用可能过期的页面。可通过 `BROWSER_TEST_PORT` 更换端口。

## 覆盖范围

| 项目 | 检查对象 | 门禁内容 |
|---|---|---|
| `desktop` | 当前检出的真实 HTML/JS | 搜索空格/大小写/空结果、等级/角色/分类/学习路径及组合筛选、统计、正文/代码/指南入口、六模块筛选、父子节点折叠、双击互斥、拖拽/滚轮/按钮缩放 |
| `mobile` | Chromium 触屏模拟 | 320×740、390×844、844×390 布局与点击，代码入口、44px 控件、横向标签滑动、拖动防误触、单击展开折叠、文档入口、平移中的双指缩放及单指续拖 |
| `desktop` 的键盘用例 | 桌面与 390px 窄屏 | Tab/Shift+Tab、所有筛选按钮的 Enter/空格、重绘后的焦点保留、方向键/Home/End、节点与文档/缩放控件间进出、可见焦点环、底部遮挡、快捷键及组合键隔离 |
| `github-readme` | GitHub 实际渲染的提交页 | Logo、六张主题图、AI 图、全景预览及赞助图，邮箱联系入口、三处折叠、重点导航链接、真实文章跳转、手机宽度与图片比例 |
| `github-readme` 的首页用例 | 公共仓库首页 | 本地运行和 main push 时，额外检查首页的同一组展示要求 |

导航数量与学习路径从当前生成清单读取；内容清单的一致性仍由原有生成门禁验证。通过真实点击、触摸输入与键盘操作断言结果，不调用页面内部函数驱动界面，不替换页面脚本、图片或 GitHub 响应。

README 的 11 张仓库配图必须加载且尺寸非零；3 个 shields.io 外部徽章校验数量、保留入口并附加加载诊断，不因第三方徽章服务暂时不可用而阻断本仓库。布局使用尺寸、可见区域与图片比例断言，并保存展示截图，不做依赖字体/平台的像素快照比较。

README 提交页还会遍历导读中的六篇 GGFramework 实践，逐篇检查唯一入口、固定提交路径、适用条件与验证边界、共用环境 / 源码 / 证据锚点，以及桌面和手机布局。按[导读的主入口表](../../../docs/工程实践/GGFramework.md#从问题选择实践入口)实际完成十组“实践 → 图谱节点 → 原实践”跳转，再检查证据锚点与返回导读的链接；不以浏览器回退代替图谱回链。

首页 GGFramework 专题必须位于六大能力域之后、AI 资料中心之前，六篇主题、导读、运行记录与 CI 复现入口在桌面和手机宽度默认可见；七个精选示例必须保留且默认收起，展开后可见、再次收起后隐藏。回归还验证导读返回首页的实际定位，以及旧 `可立即使用的资源` 锚点仍跳到工程实践区，防止调层级后丢失历史回链。

这部分验证系列阅读路径，不运行外部 Unity / ToLua、热更新发布服务、Core 包测试、渠道 SDK、认证 / 支付服务或 GGFramework 的 UI / 资源 / 网络后端。源码核对、操作预期、上游历史结果和本轮文档验证的区别统一见[系列证据分层](../../../docs/工程实践/GGFramework.md#验证方法与证据边界)。

## 当前提交与线上页面

README 默认以本地 `git rev-parse HEAD` 构造 GitHub `/blob/<SHA>/README.md` 地址；CI 使用 `github.sha`，PR 检查合并候选 SHA，避免拿旧 main 的 README 验证新改动。`README_REF` 可指定另一条已在 GitHub 可见的提交；仓库从 `GITHUB_REPOSITORY` 读取，默认 `gonglei007/GameDevMind`。本地 README 必须与该 SHA 内容一致，未提交的 README 修改应先由离线检查核对，再提交并运行真实 GitHub 检查。

本地交互测试验证当前 checkout，无须等待 Pages 发布；本地正文与代码入口读取实际文件/目录 README，不伪造 GitHub 的排版或 tree 页面。在线 blob/tree 路径与特殊字符另由现有 Node URL 回归覆盖。README 的 Pages 入口校验地址，其背后的候选交互行为由本地浏览器门禁覆盖。

公共首页代表 main，PR 只检查候选提交的 README，不把当前首页当作 PR 内容。GitHub 服务不可达、仓库私有且浏览器未认证、提交 SHA 不可见都会使在线 README 项目失败；不会静默切换成本地 Markdown 预览。

## 报告与边界

产物统一写入仓库忽略的 `output/playwright-regression/`：HTML/JSON 报告、展示截图，以及失败时的截图、trace 与视频。CI 两个 job 分别上传 `navigation-browser-report` 和 `github-readme-browser-report`，保留 7 天，测试失败仍上传已生成的产物。可在 HTML 报告中查看 trace；无需把报告发布到 Pages。

配置不自动重试或忽略失败。网络/浏览器安装失败与断言失败都返回非零。现有 Node 状态/坐标计算与 Python 内容门禁继续保留；浏览器回归补足实际布局、原生按键、触摸命中及 GitHub 展示验证。触屏模拟不等于 iOS Safari/安卓真机验收；当前固定测试 Chromium。

全景初始化的延迟居中与窗口 resize 的延迟适配，仅在调度后视图未改变时执行，避免覆盖随后发生的模块筛选、缩放或拖动。现有 `test_navigation_controls.cjs` 用可控帧与计时器验证这两类竞态，并检查无交互时仍会自动适配；手机浏览器用例继续核对放大、缩小后的中心位置，不增加等待或重试掩盖问题。

工作流见 [browser-regression.yml](../../../.github/workflows/browser-regression.yml)。两个浏览器检查均已设为 main 的必需检查；完整保护配置、17 项清单、正反向验收和 PR 更新流程见 [CI 门禁与 main 分支维护](../../../.github/CI_MAINTENANCE.md)。
