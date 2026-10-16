# GitHub Actions 工作流说明

## 必须通过的检查

所有检查均在 main 的 Push、Pull Request 和手动触发时执行，只需 `contents: read` 权限。

- [check-links.yml](check-links.yml)：离线验证发布内容的内部文件、图片链接与标题锚点。外链网络可达性不在此门禁范围内。
- [format-check.yml](format-check.yml)：检查器单元测试、正文必填字段、图片引用；另以 C++17 和 sanitizers 执行循环引用案例与网络同步回归，使用 .NET 10 执行客户端只读渲染审计的引用身份、候选过滤和快照回归。
- [generate-index.yml](generate-index.yml)：验证两个导航页共用的数据、模块目录、文档索引、关键词索引与统计是否和正文一致。

内部链接、缺图和生成漂移均使检查失败；大图片与未引用资源只报告。若要强制阻止合并，在仓库分支保护中将检查配置为必需。

客户端审计 CI 只运行不依赖 Unity 的核心；实际 Unity 2022.3 编译与只读场景回归在本地 Editor 中运行，命令见 [render_audit](../../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/README.md)。两者都不能代替目标机 URP 性能验收。

服务端优化增加 **Check Server Leaderboard Snapshot**（Go race + 独立 MySQL 8.0/Redis 7.4）和 **Check Server Lock Order**（C++17 + ASan/UBSan + 外部超时）。真实依赖配置缺失、竞态、快照/锁序回归均阻断；不使用生产数据，不把正确性测试当作容量或长期稳定性报告。命令与边界见 [服务端优化示例](../../code/gamedevmind/3.研发能力/3.2.3.服务端优化/README.md)。

## 更新索引与导航

正文标题、标签、文件列表和阅读路径是内容来源。修改后在本地运行：

```bash
python tools/check/generate_catalog.py
python tools/check/generate_catalog.py --check
```

生成脚本只更新指定生成区块，不覆盖其余手工内容。`generate-index.yml` 现在执行只读一致性检查，不再在 main 上自动提交文件；过期输出应与正文一起在 PR 中审查。

完整范围、统计口径和验证命令见 [tools/check/README.md](../../tools/check/README.md)。

## 其他维护流程

[update-readme.yml](update-readme.yml) 保留原有最近提交流程；正文统计由统一内容生成工具负责。
