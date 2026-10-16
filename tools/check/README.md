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
```

- `check_docs.py`：UTF-8、叶子文档必填字段；缺图返回非零；展示格式问题仍为告警。
- `check_links.py`：离线检查内部文件、目录、Markdown 标题锚点及 HTML ID。覆盖根目录 Markdown，以及 `mds/`、`cases/`、`ai-cases/`、`code/`、`docs/`、`tools/`、`nav/`、`.github/` 的 Markdown/HTML；排除构建产物和依赖目录。代码围栏、行内代码、HTML 注释、脚本正文中的示例不作为链接。
- `check_images.py`：检查 Markdown 图片、HTML 图片及指向图片的普通链接；缺失图片阻断，未引用和大文件只报告，不自动删除或压缩。
- `generate_catalog.py --check`：只读验证生成结果；缺失或过期时返回非零，并提示重新生成。
- 外部 URL 不在离线门禁范围内，需另行验证网络可达性。
- `template/` 是创作模板，`tmp/`、`.cursor/` 是工作资料，不作为发布内容扫描。

带 `#` 的文件名必须写成 `%23`（如 `C%23语言.md`）；路径编码与锚点用 `#` 分隔后，检查器才会正确定位。

[generate_keywords.py](generate_keywords.py) 仍可单独生成关键词索引，但提交前应运行统一生成命令。

## 案例回归

[循环引用案例](../../cases/memory-leak-slg.md) 有独立 C++17 生命周期验证程序。CI 在 Ubuntu 下启用 AddressSanitizer、LeakSanitizer 与 UndefinedBehaviorSanitizer；使用 CMake 时也可在示例目录构建后执行 `ctest --test-dir build --output-on-failure`。

[网络同步示例](../../code/gamedevmind/2.技术能力/2.2.1.网络与通信/network_sync/README.md) 还会逐帧比较确定性状态，验证输入确认、过期快照与停止输入后的预测收敛；CI 同样通过 CTest 和 sanitizers 运行。示例通过不代表真实弱网与容量指标已达标。

[客户端只读渲染审计](../../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/README.md) 的 .NET 10 核心回归已纳入 CI，验证引用身份、候选过滤、排序和快照隔离。Unity 2022.3 编译与场景只读集成回归在本地独立项目执行；这些正确性检查不代表 URP 真机提速已达标。

## CI 门禁

- [check-links.yml](../../.github/workflows/check-links.yml)：内部链接与锚点。
- [format-check.yml](../../.github/workflows/format-check.yml)：检查器回归、文档与图片、案例回归。
- [generate-index.yml](../../.github/workflows/generate-index.yml)：生成一致性。

上述失败均返回非零，不使用忽略错误继续通过的配置。要禁止失败 PR 合并，还需仓库分支保护将这些检查配置为必需状态检查。
