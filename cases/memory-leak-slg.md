# 实战案例：Shared_ptr 循环引用引发的 SLG 服务器内存泄漏

> _"内存稳如老狗，一到线上就翻车"——这是每个后端开发都逃不掉的噩梦。_

## 背景

那是 2025 年初的某个周三凌晨 2:14，我被运维的电话吵醒。

"老张，三服的进程又挂了，OOM Killer 杀的。"

这是我负责的一款 SLG 手游的后端服务器。项目上线半年，日活 50 万，整体运行还算平稳——直到这个"定时炸弹"开始爆发。

技术栈很标准：

| 组件 | 选型 |
|------|------|
| 语言 | C++17 |
| 网络库 | Boost.Asio |
| 缓存 | Redis Cluster |
| 持久化 | MySQL 8.0 |
| 部署 | Linux (CentOS 7)，物理机 8C32G |

问题的第一个信号来自 Grafana 监控面板。我发现三服的 RSS 内存曲线像一条标准的指数函数——服务启动时 800MB，然后稳步爬升，2 小时左右精准撞到 3.2GB，被内核的 OOM Killer 一刀带走。

最诡异的是：其他服务器一切正常，只有三服必死，而且时间规律极其精准——就像设了闹钟一样。

## 症状

重启服务后，问题在 2 小时后"准时"复发。我先后做了几轮尝试：

**Valgrind 线下压测——失败了。** 拉了离线环境，用同样的构建、同样的配置，跑压测脚本模拟 5000 并发玩家。跑了 4 个小时，Valgrind 的 memcheck 报告干干净净，RSS 稳定在 850MB 纹丝不动。我当时甚至怀疑是不是线上机器硬件有问题。

**线上 tcmalloc heap profile——关键线索。** 既然线下抓不到，那就线上直接抓。我们在编译时链接了 tcmalloc，通过 `HEAPPROFILE` 环境变量开启了 heap profiling：

```bash
HEAPPROFILE=/tmp/heap-profile ./game_server
```

运行 1 小时后 `pprof` dump 出来的结果让我瞳孔放大：

```
Total: 2.1 GB
  1.2 GB (57.1%): std::_Sp_counted_base<>::_M_add_ref_copy
  0.6 GB (28.6%): std::__shared_count<>::__shared_count
  ...
```

**shared_ptr 控制块的数量异常高**——正常情况下全服在线玩家 8 万左右，shared_ptr 控制块应该与活跃对象数量大致对应。但 dump 显示有超过 **30 万个** `shared_ptr<Player>` 控制块和近 **15 万个** `shared_ptr<Guild>` 控制块，而且数量还在持续增长。

这说明对象没有被正确析构，引用计数永远降不到零。

## 排查过程

### 第一步：怀疑内存池泄漏

我们自研了对象内存池来减少频繁分配。第一反应是池子本身出问题了——对象归还时没有真正回收，导致池子不断扩容。

加了每个池子的 alloc/free 计数器，运行 1 小时后拉数据：

```
PlayerPool:  alloc=92341  free=92198  in_use=143  池容量=2000
GuildPool:   alloc=15423  free=15390  in_use=33   池容量=500
```

池子正常得很。`in_use` 数量合理，池容量没有异常增长。此路不通。

### 第二步：怀疑 new/delete 不配对

接着怀疑是某处代码直接 `new` 了对象但忘记 `delete`，绕过了内存池的追踪。

重载了全局 `operator new` 和 `operator delete`，在每次分配/释放时打印地址和调用栈到环形缓冲区。跑了一个小时，对比未释放的地址和已释放的地址——全部能对上。没有裸指针泄漏。

### 第三步：线上 dump heap，锁定凶手

既然数量上是 `shared_ptr` 控制块在暴涨，那就直接看堆上到底是谁持有这些控制块。用 `pprof --gv` 生成了火焰图，顺着调用链追下去：

```
std::shared_ptr<Player>::shared_ptr  ← 大量分配
  └── Guild::AddMember()
       └── Player::JoinGuild()
```

再看 Player 析构函数的符号——**根本不在火焰图上**，意味着 Player 析构函数从来没被调用过。

这让我瞬间想到了一种可能：**循环引用**。

### 第四步：审查代码，确认根因

翻出 `Player` 和 `Guild` 的头文件，一切都清楚了。

`Player` 类中有一个成员：

```cpp
class Player {
    // ...
    std::shared_ptr<Guild> guild_;  // Player "拥有" Guild 的引用
};
```

而 `Guild` 类中：

```cpp
class Guild {
    // ...
    std::vector<std::shared_ptr<Player>> members_;  // Guild "拥有" 所有成员
};
```

**这就是经典的 shared_ptr 循环引用。** Player 持有 Guild 的 shared_ptr（引用计数+1），Guild 持有 Player 的 shared_ptr（引用计数再+1）。当玩家离开公会时，两个对象的引用计数都至少为 1（对方持有），永远无法降到 0，析构函数永远不会被调用。

## 根因分析

### 循环引用图解

```
    ┌─────────────────────────────┐
    │         Player              │
    │  shared_ptr<Guild> guild_   │──── 引用计数 +1 ────┐
    └─────────────────────────────┘                     │
           ▲                                            ▼
           │                              ┌─────────────────────────────┐
           │                              │         Guild               │
           └──── 引用计数 +1 ─────────────│ vector<shared_ptr<Player>>  │
                                          │   members_                 │
                                          └─────────────────────────────┘
```

`Player` 指向 `Guild`，`Guild` 指向 `Player`，形成一个闭环。即使外部没有任何人再引用这两个对象，它们的引用计数也至少为 1，永远无法归零。

### 为什么压测没发现？

审查压测脚本时我发现了问题——压测场景里**玩家从头到尾没有创建公会**。压测脚本只模拟了注册、登录、聊天、战斗，公会是"空"的。

当 `Player` 的 `guild_` 指针为 `nullptr` 时，循环引用不存在，对象可以正常释放。Valgrind 当然什么也报不出来。

**这是一次典型的"线下测试覆盖不全"的教训。** 线上真实玩家一定会加入公会——这是 SLG 的核心社交玩法。

### 关键代码（简化后的伪代码）

**问题代码：**

```cpp
// player.h
class Player : public std::enable_shared_from_this<Player> {
public:
    void JoinGuild(std::shared_ptr<Guild> guild) {
        guild_ = guild;
        guild->AddMember(shared_from_this());  // 这里建立循环引用
    }

    void LeaveGuild() {
        if (guild_) {
            guild_->RemoveMember(GetId());
            guild_.reset();  // BUG: 这里 reset 了，但 Guild 那边的 shared_ptr 还在！
        }
    }

private:
    std::shared_ptr<Guild> guild_;  // Player → Guild
};

// guild.h
class Guild {
public:
    void AddMember(std::shared_ptr<Player> player) {
        members_.push_back(player);  // Guild → Player，建立循环引用
    }

    void RemoveMember(uint64_t player_id) {
        // BUG: 这里的 erase 只删除了元素，但 shared_ptr 的引用计数问题已经形成
        members_.erase(
            std::remove_if(members_.begin(), members_.end(),
                [player_id](const auto& p) { return p->GetId() == player_id; }),
            members_.end()
        );
    }

private:
    std::vector<std::shared_ptr<Player>> members_;  // 持有所有成员的 shared_ptr
};
```

`LeaveGuild()` 虽然调用了 `guild_.reset()`，但 `Guild::members_` 中的 `shared_ptr<Player>` 还在，Player 的引用计数没有归零。而 Player 不析构，它持有的 `guild_` 也不会释放，于是 Guild 的引用计数也无法归零。完美闭环，精准泄漏。

## 解决方案

问题的本质是**所有权语义混乱**：

- `Player` 持有 `shared_ptr<Guild>`：合理，玩家需要知道自己属于哪个公会，且玩家生命期比公会短时可以接受。
- `Guild` 持有 `vector<shared_ptr<Player>>`：不合理。公会不应该"拥有"玩家——玩家的生命期由网络连接决定，公会只需要"观察"当前有哪些玩家在线。

修改方案很明确——将 `Guild` 中对 Player 的持有从 `shared_ptr` 改为 `weak_ptr`：

```cpp
// guild.h — 修复后
class Guild {
public:
    void AddMember(std::shared_ptr<Player> player) {
        members_.push_back(player);  // shared_ptr → weak_ptr 隐式转换，不增加引用计数
    }

    void RemoveMember(uint64_t player_id) {
        members_.erase(
            std::remove_if(members_.begin(), members_.end(),
                [player_id](const auto& wp) {
                    auto sp = wp.lock();
                    return !sp || sp->GetId() == player_id;
                }),
            members_.end()
        );
    }

    // 遍历成员时需要用 lock() 检查对象是否还存活
    void BroadcastToMembers(const std::string& msg) {
        for (auto& wp : members_) {
            if (auto player = wp.lock()) {
                player->SendMessage(msg);
            }
            // 如果 lock() 返回空，说明 Player 已经析构，自动跳过
        }
    }

private:
    std::vector<std::weak_ptr<Player>> members_;  // 只"观察"玩家，不拥有
};
```

**为什么这样改是对的：**

| 关系 | 修改前 | 修改后 | 所有权语义 |
|------|--------|--------|------------|
| Player → Guild | `shared_ptr` | `shared_ptr`（不变） | Player 需要 Guild 的信息才能运作 |
| Guild → Player | `shared_ptr` | `weak_ptr` | Guild 只是"观察"成员列表 |

`weak_ptr` 不增加引用计数，打破了循环。当玩家断开连接、Player 对象的外部引用全部释放后，引用计数归零，Player 正常析构。析构时释放 `guild_`，Guild 的引用计数也相应减少。

`lock()` 的开销微乎其微——它只是一个原子操作检查控制块中的 `use_count`，相比服务器其他逻辑可以忽略不计。

## 效果

修复上线后的监控数据让我终于睡了个好觉：

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 2 小时 RSS | 3.2 GB（OOM） | 880 MB |
| 72 小时 RSS | —（进程已死） | 910 MB |
| 7 天 RSS 峰值 | — | 950 MB |
| shared_ptr 控制块峰值 | 45 万+ | ~12 万（正常波动） |
| 进程稳定性 | 2 小时必挂 | 持续运行 30 天无重启 |

> 改后运行了 72 小时压测，RSS 稳定在 900MB 左右，内存曲线像一条水平线。后来在线上跑了整整一个月没重启，运营同学都来问我是不是偷偷优化了服务器——"最近怎么没崩过了？"

## 经验教训

### 1. shared_ptr 不是银弹——循环引用会静默泄漏

这是 C++ 面试八股文里的经典题目，但在真实项目中踩到时，还是排查了好几天。shared_ptr 的引用计数机制决定了：只要存在环，环上的所有对象都永远不会被释放。而且这种泄漏**没有崩溃、没有报错、没有 Core Dump**——它只是安静地吃内存，直到 OOM。

### 2. 所有权 vs 观察权——区分清楚才能用对智能指针

这是一个很好的设计原则：

- **`unique_ptr`**：独占所有权，生命周期唯一
- **`shared_ptr`**：共享所有权，最后一个持有者负责释放
- **`weak_ptr`**：无所有权，仅"观察"，不参与生命周期管理

在写代码时就应该问自己：这个对象"拥有"另一个对象吗？还是只需要"知道"它的存在？答案决定了用什么指针。

### 3. 线下压测必须覆盖线上真实场景

这是我们这次最大的教训。压测脚本缺少公会系统的场景覆盖，导致最核心的社交模块在压测时完全没有被测试到。后续我们调整了压测策略：

- 压测脚本必须覆盖所有核心业务模块（公会、联盟、排行榜等）
- 新增"场景回放"机制：从线上日志采样真实玩家行为序列，在压测中重放
- 每个模块必须有独立的压力测试用例

### 4. 加监控——让泄漏无处可藏

事后我们在监控体系里加了几个关键指标：

```
# Prometheus 指标示例
game_shared_ptr_control_block_count{type="Player"}   # Player 控制块数量
game_shared_ptr_control_block_count{type="Guild"}     # Guild 控制块数量
game_object_pool_in_use{pool="Player"}                # 对象池活跃数
```

当 shared_ptr 控制块数量与在线玩家数之比超过某个阈值（比如 1.5）时，自动触发告警。这样以后再出现类似问题，能在 OOM 之前就发现。

### 5. 用 AddressSanitizer 做 CI 防线

最后我们在 CI 流水线中加了 AddressSanitizer（ASan）构建：

```cmake
# CMakeLists.txt
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fsanitize=address -fno-omit-frame-pointer")
```

虽然 ASan 主要检测越界和 use-after-free，但它的 LeakSanitizer 组件也能在进程退出时报告未释放的内存块。配合压测脚本，能在合并代码之前就拦截内存泄漏。

---

## 图谱知识点映射

| 知识点 | 路径 | 关联内容 |
|--------|------|----------|
| C++ 语言 — 智能指针 | [C++语言](../mds/1.基础能力/1.1.2.C++语言.md) | shared_ptr / weak_ptr / unique_ptr 的使用场景与陷阱 |
| 内存管理 | [内存管理](../mds/1.基础能力/1.1.6.内存管理.md) | 循环引用检测、内存泄漏排查方法论 |
| 配套代码示例 | [智能指针陷阱](../code/gamedevmind/1.基础能力/1.1.2.C++语言/smart_pointer/) | 循环引用的最小可复现示例与修复方案 |

---

> **一句话总结：谁拥有谁用 shared_ptr，谁观察谁用 weak_ptr。别让两个 shared_ptr 互相看着对方，那是一场无声的内存葬礼。**
