## UI 系统架构 — 配套代码

对应文章：二-03-游戏 UI 系统架构设计：关键模块与取舍

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 布局系统 / 锚点 | `ui_layout.py` | 9 种锚点预设、Flexbox 对齐 |
| 事件系统 | `ui_layout.py` | 捕获→目标→冒泡三阶段模型 |
| UIManager / 面板栈 | 正文为 C# 骨架 | Unity UGUI 完整实现见 GameDevMind |

### 运行

```bash
python ui_layout.py
```

纯标准库，无需安装依赖。

### 核心概念

| 系统 | 对标 | 核心类 |
|------|------|--------|
| 锚点 | Unity RectTransform | `Anchor`, `AnchorPreset` |
| 弹性盒子 | CSS Flexbox | `FlexLayout` |
| 事件冒泡 | DOM Event Model | `UIEvent`, `UIElement.dispatch_event()` |

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
