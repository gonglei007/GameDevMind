## 任务系统开发 — 配套代码

对应文章：三-07-任务系统开发指南：类型／进度／奖励

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 任务数据结构 / 状态机 | `quest_system.py` | Locked→Available→Active→Completed→Claimed |
| 主线 / 每日 / 成就 | `quest_system.py` | 接取校验、5 点重置、成就累加 |
| 进度追踪 | `quest_system.py` | 事件驱动更新 objective |
| 奖励发放 | `quest_system.py` | 幂等领奖 |
| 任务链 | `quest_system.py` | 有序 taskIds + index 推进 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 任务状态机 | `quest_system.py` | 接取、进度、领奖、任务链完整流程 |

### 设计要点

- **状态机**: Locked → Available → Active → Completed → Claimed
- **任务链**: 前置任务依赖，按序推进 currentTaskIndex
- **进度追踪**: 多目标 progress 更新与完成检测
- **每日重置**: 服务端权威 resetTime 比较

### 运行

```bash
python3 quest_system.py
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
