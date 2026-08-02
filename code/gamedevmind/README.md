# 🎮 GameDevMind 配套代码示例

本目录包含《游戏开发技术图谱》的配套可运行代码示例，每个示例直接对应 `mds/` 中的知识文档。

> 集合根目录：[code/](../) · 本集合路径：`code/gamedevmind/`

## 📂 目录结构

```
code/gamedevmind/
├── 1.基础能力/
│   ├── 1.1.2.C++语言/
│   │   ├── memory_pool/        ← 游戏服务器内存池
│   │   └── smart_pointer/      ← 智能指针最佳实践与陷阱
│   ├── 1.1.3.C#语言/
│   │   └── object_pool/        ← C# 对象池（Unity 子弹/粒子）
│   ├── 1.2.1.设计模式/
│   │   ├── command/            ← 命令模式（游戏输入/回放）
│   │   └── object_pool/        ← 对象池（C++ 版）
│   └── 1.2.2.数据结构/
│       └── quadtree/           ← 四叉树（空间分区/碰撞检测）
├── 2.技术能力/
│   └── 2.2.1.网络与通信/
│       └── network_sync/       ← 帧同步 vs 状态同步对比
├── 3.研发能力/
│   └── 3.1.2.客户端3D场景开发/
│       └── hex_grid/           ← 六边形网格 + A* 寻路
├── 4.生产能力/
│   └── 4.2.3.游戏数据文件/
│       └── excel_to_json/      ← Excel 策划表 → JSON
└── 6.运营能力/
    └── 6.2.3.产品热更新/
        └── hotupdate_client/   ← 热更新 manifest 最小流程
```

## 🚀 快速开始

每个示例目录包含独立的 `CMakeLists.txt`、`dotnet` 项目或 Python 脚本：

```bash
# C++ 示例
cd code/gamedevmind/1.基础能力/1.1.2.C++语言/memory_pool
mkdir build && cd build && cmake .. && make && ./memory_pool

# C# 示例
cd code/gamedevmind/1.基础能力/1.1.3.C#语言/object_pool && dotnet run

# Python 示例
cd code/gamedevmind/6.运营能力/6.2.3.产品热更新/hotupdate_client && python hotupdate_client.py
```

## 📖 示例与图谱对应关系

| 示例 | 对应文档 | 核心知识点 |
|------|----------|------------|
| [memory_pool](1.基础能力/1.1.2.C++语言/memory_pool/) | [C++语言](../../../mds/1.基础能力/1.1.2.C++语言.md) | 内存分配策略、内存碎片、池化技术 |
| [smart_pointer](1.基础能力/1.1.2.C++语言/smart_pointer/) | [C++语言](../../../mds/1.基础能力/1.1.2.C++语言.md) | unique_ptr/shared_ptr/weak_ptr、循环引用 |
| [object_pool (C#)](1.基础能力/1.1.3.C#语言/object_pool/) | [C#语言](../../../mds/1.基础能力/1.1.3.C#语言.md) | Get/Release、GC 优化 |
| [command](1.基础能力/1.2.1.设计模式/command/) | [设计模式](../../../mds/1.基础能力/1.2.1.设计模式.md) | 命令队列、撤销重做、输入录制回放 |
| [object_pool (C++)](1.基础能力/1.2.1.设计模式/object_pool/) | [设计模式](../../../mds/1.基础能力/1.2.1.设计模式.md) | 对象复用、预分配、性能优化 |
| [quadtree](1.基础能力/1.2.2.数据结构/quadtree/) | [数据结构](../../../mds/1.基础能力/1.2.2.数据结构.md) | 空间分区、碰撞检测、近邻查询 |
| [network_sync](2.技术能力/2.2.1.网络与通信/network_sync/) | [网络与通信](../../../mds/2.技术能力/2.2.1.网络与通信.md) | 帧同步、状态同步、插值与预测 |
| [hex_grid](3.研发能力/3.1.2.客户端3D场景开发/hex_grid/) | [客户端3D场景开发](../../../mds/3.研发能力/3.1.2.客户端3D场景开发.md) | 六边形坐标、A*寻路、地形生成 |
| [excel_to_json](4.生产能力/4.2.3.游戏数据文件/excel_to_json/) | [游戏数据文件](../../../mds/4.生产能力/4.2.3.游戏数据文件.md) | 策划表导出、类型校验、CI 集成 |
| [hotupdate_client](6.运营能力/6.2.3.产品热更新/hotupdate_client/) | [产品热更新](../../../mds/6.运营能力/6.2.3.产品热更新.md) | manifest、增量下载、MD5 校验 |

## 🤝 贡献代码示例

欢迎贡献更多代码示例！请参考 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解规范。

**代码示例要求：**
1. 可独立编译运行（CMake / dotnet / Python 等）
2. 包含详细注释，解释关键概念
3. 附带 `README.md` 说明运行方法和知识点映射
4. 命名规范：`code/gamedevmind/模块/文档编号/示例名/`
