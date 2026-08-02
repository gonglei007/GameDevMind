## DevOps 实践 — 配套代码

对应文章：四-06-游戏 DevOps 实践：持续集成、持续交付

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| CI / Jenkins Pipeline | `ci_pipeline.py` | Checkout→Test→Build 阶段模拟 |
| CD / Docker 部署 | 正文 Dockerfile 骨架 | compose 与健康检查扩展 |
| 自动化运维 | `ci_pipeline.py` | 部署脚本与健康探测 |
| 监控告警 | 正文 prometheus/alerts 骨架 | Grafana 看板扩展 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| CI 流水线模拟 | `ci_pipeline.py` | 构建、测试门禁、部署与健康检查流程 |

### 设计要点

- **流水线阶段**: 拉代码 → 跑测试 → 构建 → 归档/通知
- **门禁**: 测试不通过阻断后续发布
- **健康检查**: 部署后 curl /health 验证服务可用
- **可观测**: 构建失败邮件/日志，便于快速定位

### 运行

```bash
python3 ci_pipeline.py
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
