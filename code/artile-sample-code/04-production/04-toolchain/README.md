## 工具链建设 — 配套代码

对应文章：四-04-游戏开发工具链建设

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 多平台构建流程 | `build_tool.py` | iOS/Android/Web/PC 构建步骤模拟、版本号递增、构建报告 |

### 文章章节覆盖

- **CI/CD**：Jenkins Pipeline 阶段、GitLab CI stages、Docker 部署
- **自动化测试**：单元 / 集成 / E2E 测试层次与 Unity Test Framework
- **构建系统**：Unity BuildScript、Gradle 版本号自动递增
- **监控告警**：Prometheus scrape、Grafana 看板指标

### 运行

```bash
python3 build_tool.py
```
