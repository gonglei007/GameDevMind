## 客户端架构设计 — 配套代码

对应文章：三-01-游戏客户端架构怎么设计？从需求到演进

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 客户端架构基础 / MVC | `mvc_demo.py` | Model/View/Controller 分离，终端演示 |
| 游戏循环 / 更新顺序 | `mvc_demo.py` 主循环 | 输入 → 逻辑 → 渲染的简化循环 |
| 场景 / 资源 / ECS | 正文为设计骨架 | 可按文章接口在 Unity 项目中扩展；需要完整 C# 时可从 GameDevMind 生成 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| MVC 模式演示 | `mvc_demo.py` | 角色数据 + 终端 UI + WASD 输入控制 |

### 设计要点

- **Model**：角色数据与业务逻辑，纯 Python 类，不依赖 UI
- **View**：观察者模式订阅 Model 变化，终端渲染角色面板
- **Controller**：WASD 移动 / 战斗 / 治疗 / 背包，逐帧输入循环

### 运行

```bash
python3 mvc_demo.py
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
