# 游戏服务器内存池 (Memory Pool)

> 📂 对应知识图谱章节：`1.基础能力 / 1.1.2.C++语言 / 内存`  
> 📄 图谱文档：`mds/1.基础能力/1.1.2.C++语言.md` → 「内存」章节

---

## 1. 内存池是什么？

**内存池（Memory Pool）** 是一种预先分配一大块连续内存、然后在应用层自行管理分配/回收的技术。它的核心思想是：**一次向操作系统要一大块，之后所有"分配"只需从池里拿，"释放"只需归还到池里，不再经过 `malloc/free` 系统调用**。

### 工作原理

```
传统 malloc/free：
  请求32B → 系统调用(mmap/brk) → 内核分配 → 返回指针
  释放32B → 系统调用(munmap/brk) → 内核回收
  （每次都有上下文切换 + 碎片管理开销）

内存池（本项目实现）：
  初始化 → 预分配 1000 × sizeof(NPC) 的连续内存
           内部串联成自由链表：
           [block0] → [block1] → [block2] → ... → [block999] → nullptr

  分配(Allocate) → 从链表头部摘取一块，返回指针 ── O(1) 无系统调用
  释放(Deallocate) → 把块插回链表头部 ── O(1) 无系统调用
```

### 关键数据结构：自由链表（Free List）

所有空闲块通过每个块的头 8 个字节（指针大小）串联成一个单链表。当一个块被分配时，这 8 字节被对象数据覆盖；当它被释放时，这 8 字节重新被用作链表指针。**零额外内存开销**。

---

## 2. 适用场景

### 游戏服务器 NPC 管理

```
场景：一个区域服同时在线 10,000 个玩家，视野内平均 200 个 NPC。
      NPC 频繁进入/离开视野（相当于频繁创建/销毁对象）。

传统做法：
  NPC* npc = new NPC(...);   // 进入视野
  delete npc;                // 离开视野
  → 每秒数千次 malloc/free，内存碎片逐渐累积，最终导致：
    "总空闲 500MB，但找不到一块连续的 64KB"

内存池做法：
  static MemoryPool<NPC, 1000> npc_pool;  // 预分配 1000 个 NPC 槽位
  NPC* npc = npc_pool.New(...);           // 进入视野
  npc_pool.Delete(npc);                   // 离开视野
  → 无系统调用，无碎片，分配耗时恒定 ~10ns
```

### 粒子系统

```
场景：技能特效产生大量粒子（火球/冰锥/箭雨），每个粒子生命周期 0.5~2 秒。
      每帧可能有 500+ 粒子创建、300+ 粒子销毁。

内存池做法：
  MemoryPool<Particle, 5000> particle_pool;
  → 预分配 5000 个粒子槽位，循环复用
  → 保证帧率稳定，不会因 malloc 尖刺导致卡顿
```

### 其他适用场景

| 场景 | 对象类型 | 典型池大小 |
|------|----------|-----------|
| 子弹/Bullet | 弹道对象 | 2000~5000 |
| 网络包缓冲 | 固定大小 Buffer | 4096+ |
| AI 行为树节点 | 小对象（<128B） | 10000+ |
| 数据库连接 | 连接对象 | 50~200 |
| 日志事件 | 日志条目 | 10000+ |

### 不适用场景

- 对象大小不固定（需要通用 allocator）
- 对象生命周期极长且不可预测（池一直占着内存）
- 需要跨线程无锁分配（需要额外实现 Lock-Free 或 Thread-Local Pool）

---

## 3. 本项目文件说明

```
memory_pool/
├── memory_pool.hpp   # 模板化内存池头文件（核心实现）
├── main.cpp           # 性能对比 + 碎片演示 + 安全检测
├── CMakeLists.txt     # CMake 构建配置（C++17）
└── README.md          # 本文件
```

### memory_pool.hpp 核心 API

```cpp
// 定义一个管理 1000 个 NPC 对象的内存池
gdm::MemoryPool<NPC, 1000> pool;

// 分配 — 仅获取内存，不调用构造函数
NPC* npc = pool.Allocate();
::new (npc) NPC(...);  // placement new

// 释放 — 需手动析构
npc->~NPC();
pool.Deallocate(npc);

// 快捷方法 — 自动调用构造/析构
NPC* npc = pool.New(id, x, y, z);   // 分配 + 构造
pool.Delete(npc);                    // 析构 + 释放

// 查询
size_t avail = pool.Available();     // 当前空闲块数
size_t cap   = pool.Capacity();      // 池总容量 (编译期常量)
```

### DEBUG 模式安全检测

使用 Debug 编译时（`CMAKE_BUILD_TYPE=Debug`），内存池会在每个块前后放置**哨兵值（Canary）**，并在每次操作时校验：

| 检测项 | 原理 | 触发时机 |
|--------|------|----------|
| **越界写入** | 块后 4 字节哨兵 `0xC0DEDEAD` | Deallocate 时校验 |
| **越界前写** | 块前 4 字节哨兵 `0xDEADC0DE` | Allocate 时校验 |
| **Double-Free** | 元数据 `allocated` 标志位 | Deallocate 时校验 |
| **非法指针** | 地址不落在池范围内 | Allocate/Deallocate 时断言 |

> ⚠️ 注意：DEBUG 模式下的哨兵和元数据会额外占用内存，不适合性能测试。

---

## 4. 运行方法

### 环境要求

- CMake ≥ 3.14
- 支持 C++17 的编译器（GCC 8+, Clang 7+, MSVC 2019+）
- 操作系统：Linux / macOS / Windows

### 编译 & 运行

```bash
# 进入项目目录
cd code/gamedevmind/1.基础能力/1.1.2.C++语言/memory_pool

# ====== Release 模式（性能测试） ======
cmake -B build_release -DCMAKE_BUILD_TYPE=Release
cmake --build build_release
./build_release/memory_pool_demo

# ====== Debug 模式（安全检测演示） ======
cmake -B build_debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build_debug
./build_debug/memory_pool_demo
```

### 预期输出示例

```
╔══════════════════════════════════════════════════════════════╗
║  测试1：malloc/free vs MemoryPool 分配/释放性能         ║
║  场景：游戏服务器每帧创建并销毁 200 个 NPC              ║
╚══════════════════════════════════════════════════════════════╝

  malloc/free  :   500 帧 × 200 NPC
  ──────────────────────────────────
  总耗时        : 15234.5 us
  单次操作      : 0.076 us (alloc+free)

  MemoryPool   :   500 帧 × 200 NPC
  ──────────────────────────────────
  总耗时        : 2134.8 us
  单次操作      : 0.011 us (alloc+free)

  🚀 内存池加速  : ×7.14 (更快)
```

---

## 5. 设计决策与权衡

| 决策 | 理由 |
|------|------|
| **模板化固定大小** | 编译期确定容量，零运行时开销，数组分配在栈/数据段上（无堆分配） |
| **自由链表嵌入块内** | 不额外占用内存，利用对象自身的存储空间 |
| **禁止拷贝/移动** | 池拥有底层原始内存，拷贝会导致双重释放 |
| **显式 Allocate/Deallocate** | 与构造/析构分离，贴合游戏服务器中"对象复用"的惯用法 |
| **DEBUG 哨兵** | 仅 Debug 编译启用，Release 零开销 |
| **不自动调用析构** | 池的析构函数不遍历所有块调用析构——由调用者保证归还 |

---

## 6. 延伸阅读

- **C++ 标准库内存池**：`std::pmr::synchronized_pool_resource` / `std::pmr::unsynchronized_pool_resource`（C++17）
- **游戏引擎实践**：
  - Unreal Engine：`FMemory` / `TMemStackAllocator`
  - Unity：`NativeArray` + `Allocator.Temp`
- **经典文献**：
  - _Fast Efficient Fixed-Size Memory Pool_ — Ben Kenwright
  - _Memory Management: Algorithms and Implementations_ — Bill Blunden
- **对应图谱章节**：`mds/1.基础能力/1.1.2.C++语言.md` 的「内存」部分详细讨论了智能指针、RAII、内存池等 C++ 内存管理技术。
