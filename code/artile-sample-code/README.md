# 📦 《游戏开发者应知》文章配套样例代码

> 知乎专栏连载：[《游戏开发图谱》](https://www.zhihu.com/column/c_201511624283)  
> 作者：[公雷](https://www.zhihu.com/people/gonglei)  
> 集合路径：`code/artile-sample-code/` · 上级索引：[code/](../)

本目录为专栏 / 书籍文章中引用的可运行样例（以 Python 标准库为主，少量 C++），与图谱配套集合 [`gamedevmind/`](../gamedevmind/) 并列维护。

---

## 🚀 快速开始

在仓库根目录或本目录下直接运行（零第三方依赖）：

```bash
cd code/artile-sample-code

python 01-foundation/03-data-structures/quadtree.py
python 03-rd/03-sync/net_sync.py
python 07-special/05-all-in-one/mini_game.py
```

C++ 设计模式示例（需 g++）：

```bash
make            # 编译 01-foundation/02-design-patterns/*.cpp
make test       # 运行编译产物 + 若干 Python 示例
```

---

## 🗺️ 代码全景（约 43 个可运行示例）

| 篇章 | 示例数 | 亮点 |
|------|:--:|------|
| **一、基础能力篇** | 7 | 语言性能对比 · 设计模式 · 四叉树 · AoS/SoA · TCP/UDP |
| **二、技术能力篇** | 8 | 渲染管线 · 物理模拟 · UI 布局 · 引擎选型 · 消息序列化 |
| **三、研发能力篇** | 8 | MVC 架构 · 游戏服务器 · 网络同步 · 战斗公式 · 摄像机 |
| **四、生产能力篇** | 6 | 资源管线 · AI 生成 · CI/CD · 平台抽象 · 构建工具链 |
| **五、管理能力篇** | 6 | 工作流 · 代码质量 · 项目管理 · Scrum |
| **六、运营能力篇** | 8 | 服务器监控 · GM 命令 · 数据分析 · 热更新 · 反作弊 |
| **七、专题篇** | 4 | 学习路线 · 职业路径 · 创业预算 · 完整 RPG |
| **AI Coding / AI 社会** | 2 | AI 生成背包系统 · 财富分配模拟 |

各子目录 README 中的「对应文章」标题与专栏章节一致；正文见知乎专栏，图谱知识文档见仓库 [`mds/`](../../mds/)。

---

## 🎯 用途

- 配合专栏文章边读边跑
- 面试常考：数据结构、设计模式、网络同步等可直接演示
- 对象池、事件系统、状态机等可作项目起点
- 作为 AI 编程上下文，快速生成变体

---

## 📚 相关入口

- 知乎专栏：https://www.zhihu.com/column/c_201511624283
- 专栏文章索引：[知乎文章参考.md](../../知乎文章参考.md)
- 图谱配套示例（C++/C#）：[gamedevmind/](../gamedevmind/)

---

*导入自文章样例库 · Python 3 标准库 · 零外部依赖*
