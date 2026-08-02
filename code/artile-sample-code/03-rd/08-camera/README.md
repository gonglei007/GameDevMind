## 摄像机控制 — 配套代码

对应文章：三-08-游戏摄像机控制：第三人称／第一人称／固定视角

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 第三人称 / 跟随 | `camera_system.py` | lerp 平滑跟随目标 |
| 碰撞 / 边界 | `camera_system.py` | 距离限制与边界 clamp |
| 第一人称 / 摆动 | 正文 LateUpdate 骨架 | 头部 bob 扩展 |
| 固定 / 电影机位 | 正文 SwitchToAngle 骨架 | 关键帧插值扩展 |
| 透明化遮挡 | 正文 SphereCastAll 骨架 | 材质 alpha 处理 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 摄像机系统 | `camera_system.py` | 平滑跟随、震屏、视野缩放、边界限制 |

### 设计要点

- **LateUpdate 跟随**: 在角色/动画更新后再移动摄像机，避免抖动
- **平滑插值**: lerp 过渡 position，避免硬切
- **震屏效果**: 衰减强度模拟冲击反馈
- **边界限制**: clamp 摄像机坐标在 min/max 范围内

### 运行

```bash
python3 camera_system.py
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
