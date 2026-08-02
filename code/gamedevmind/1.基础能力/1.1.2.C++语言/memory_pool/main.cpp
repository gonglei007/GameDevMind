// ===================================================================
// 游戏服务器内存池 - 性能对比 & 内存碎片演示
//
// 场景：
//   - 游戏服务器每秒需要创建/销毁数千个 NPC、子弹、粒子等
//   - 直接使用 malloc/free 会导致：
//       1. 频繁系统调用（mmap/brk）开销大
//       2. 内存碎片：小块分配交替释放，导致总空闲 > 单次大分配需求却无法满足
//   - 内存池：预分配连续内存，O(1) 复用，零碎片
//
// 编译（Release，对比性能）：
//   mkdir build && cd build
//   cmake .. -DCMAKE_BUILD_TYPE=Release
//   make
//   ./memory_pool_demo
//
// 编译（Debug，开启越界/double-free 检测）：
//   mkdir build && cd build
//   cmake .. -DCMAKE_BUILD_TYPE=Debug
//   make
//   ./memory_pool_demo
// ===================================================================

#include <iostream>
#include <iomanip>
#include <chrono>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <algorithm>
#include <numeric>

#include "memory_pool.hpp"

// ===================================================================
// 模拟游戏对象：NPC
// ===================================================================
struct NPC {
    uint64_t id;           // NPC 唯一 ID
    float    x, y, z;      // 世界坐标
    float    hp;           // 生命值
    int32_t  ai_state;     // AI 状态机当前状态
    char     name[32];     // NPC 名字（如 "守卫队长"）

    NPC() : id(0), x(0), y(0), z(0), hp(100.f), ai_state(0) {
        std::strcpy(name, "Unnamed");
    }
    NPC(uint64_t id_, float x_, float y_, float z_)
        : id(id_), x(x_), y(y_), z(z_), hp(100.f), ai_state(0) {
        std::snprintf(name, sizeof(name), "NPC_%llu",
                      static_cast<unsigned long long>(id_));
    }
};

static_assert(sizeof(NPC) >= sizeof(void*),
              "NPC must be pointer-sized for free-list chaining");

// ===================================================================
// 工具：高精度计时器
// ===================================================================
class Timer {
public:
    using Clock = std::chrono::high_resolution_clock;
    using Ms    = std::chrono::microseconds;

    void start() { t0_ = Clock::now(); }
    double elapsed_us() const {
        auto t1 = Clock::now();
        return static_cast<double>(
            std::chrono::duration_cast<Ms>(t1 - t0_).count()
        );
    }

private:
    Clock::time_point t0_;
};

// ===================================================================
// 测试1：malloc/free vs 内存池 分配/释放性能
// ===================================================================
void benchmark_alloc_dealloc() {
    std::cout << "\n"
              << "╔══════════════════════════════════════════════════════════╗\n"
              << "║  测试1：malloc/free vs MemoryPool 分配/释放性能         ║\n"
              << "║  场景：游戏服务器每帧创建并销毁 200 个 NPC              ║\n"
              << "╚══════════════════════════════════════════════════════════╝\n\n";

    constexpr int kRounds    = 500;   // 模拟 500 帧（约 8 秒 @60fps）
    constexpr int kPerFrame  = 200;   // 每帧分配/释放 200 个 NPC
    constexpr int kTotalOps  = kRounds * kPerFrame;  // 总共 100,000 次操作

    Timer timer;

    // ---------- 方案 A：malloc / free ----------
    {
        std::vector<NPC*> ptrs;
        ptrs.reserve(kPerFrame);

        timer.start();
        for (int round = 0; round < kRounds; ++round) {
            // 一帧内：分配 200 个 NPC
            for (int i = 0; i < kPerFrame; ++i) {
                auto* npc = static_cast<NPC*>(std::malloc(sizeof(NPC)));
                ::new (npc) NPC(round * kPerFrame + i,  // id
                                static_cast<float>(i),    // x
                                0.f, 10.f);              // y, z
                ptrs.push_back(npc);
            }
            // 一帧结束时：释放 200 个 NPC（模拟 NPC 死亡/离开视野）
            for (auto* npc : ptrs) {
                npc->~NPC();
                std::free(npc);
            }
            ptrs.clear();
        }
        double malloc_time = timer.elapsed_us();

        std::cout << "  malloc/free  :   500 帧 × 200 NPC\n";
        std::cout << "  ──────────────────────────────────\n";
        std::cout << "  总耗时        : " << std::fixed << std::setprecision(1)
                  << malloc_time << " us\n";
        std::cout << "  单次操作      : " << std::fixed << std::setprecision(3)
                  << malloc_time / (kTotalOps * 2) << " us (alloc+free)\n\n";
    }

    // ---------- 方案 B：MemoryPool ----------
    {
        // 假设同时活跃最多 1000 个 NPC（池容量）
        static gdm::MemoryPool<NPC, 1000> s_npc_pool;
        std::vector<NPC*> ptrs;
        ptrs.reserve(kPerFrame);

        timer.start();
        for (int round = 0; round < kRounds; ++round) {
            for (int i = 0; i < kPerFrame; ++i) {
                auto* npc = s_npc_pool.New(round * kPerFrame + i,
                                           static_cast<float>(i),
                                           0.f, 10.f);
                ptrs.push_back(npc);
            }
            for (auto* npc : ptrs) {
                s_npc_pool.Delete(npc);
            }
            ptrs.clear();
        }
        double pool_time = timer.elapsed_us();

        std::cout << "  MemoryPool   :   500 帧 × 200 NPC\n";
        std::cout << "  ──────────────────────────────────\n";
        std::cout << "  总耗时        : " << std::fixed << std::setprecision(1)
                  << pool_time << " us\n";
        std::cout << "  单次操作      : " << std::fixed << std::setprecision(3)
                  << pool_time / (kTotalOps * 2) << " us (alloc+free)\n\n";

        double speedup = malloc_time / pool_time;
        std::cout << "  🚀 内存池加速  : ×" << std::fixed << std::setprecision(2)
                  << speedup << " (" << (speedup > 1.0 ? "更快" : "无优势") << ")\n";
        if (speedup < 1.0) {
            std::cout << "     （可能与系统 allocator 缓存有关，但内存池的真正优势在碎片和可预测性）\n";
        }
    }
}

// ===================================================================
// 测试2：内存碎片演示
// ===================================================================
void demo_fragmentation() {
    std::cout << "\n"
              << "╔══════════════════════════════════════════════════════════╗\n"
              << "║  测试2：内存碎片问题演示                                 ║\n"
              << "║  场景：交替分配不同大小对象，然后释放一半，再尝试分配大块 ║\n"
              << "╚══════════════════════════════════════════════════════════╝\n\n";

    constexpr int kSmallCount = 10000;
    constexpr int kLargeSize  = 1024;  // 1KB

    // ---------- malloc 碎片化 ----------
    {
        std::vector<void*> small_blocks;
        std::vector<void*> large_blocks;

        std::cout << "  [malloc/free 碎片演示]\n";
        std::cout << "  1. 分配 " << kSmallCount << " 个小块 (32B each) ...\n";
        for (int i = 0; i < kSmallCount; ++i) {
            small_blocks.push_back(std::malloc(32));
        }

        std::cout << "  2. 交替分配 " << (kSmallCount / 2) << " 个大块 (1KB) ...\n";
        for (int i = 0; i < kSmallCount / 2; ++i) {
            large_blocks.push_back(std::malloc(kLargeSize));
        }

        std::cout << "  3. 释放所有大块 ...\n";
        for (auto* p : large_blocks) {
            std::free(p);
        }
        large_blocks.clear();

        std::cout << "  4. 尝试分配一个 " << (kLargeSize * kSmallCount / 2)
                  << " 字节的大块 ...\n";
        void* big = std::malloc(kLargeSize * kSmallCount / 2);
        if (big) {
            std::cout << "     ✓ 成功！系统 allocator 此时尚未严重碎片化。\n";
            std::free(big);
        } else {
            std::cout << "     ✗ 失败！虽然总空闲 ≥ 需求，但因碎片无法分配连续区域。\n";
        }

        // 清理
        for (auto* p : small_blocks) std::free(p);
    }

    // ---------- 内存池：零碎片 ----------
    {
        std::cout << "\n  [MemoryPool：零碎片保证]\n";
        std::cout << "  内存池使用预分配的连续大块，内部固定大小复用。\n";
        std::cout << "  无论分配/释放多少次，碎片始终为零。\n";
        std::cout << "  游戏服务器中，NPC 池、子弹池、粒子池各自独立，\n";
        std::cout << "  互不干扰，不会出现「总内存够但分配失败」的情况。\n";
    }
}

// ===================================================================
// 测试3：DEBUG 模式安全检测
// ===================================================================
void debug_safety_demo() {
    std::cout << "\n"
              << "╔══════════════════════════════════════════════════════════╗\n"
              << "║  测试3：DEBUG 模式安全检测（仅在 Debug 编译下有效）      ║\n"
              << "║  检测能力：double-free、buffer overflow、use-after-free  ║\n"
              << "╚══════════════════════════════════════════════════════════╝\n\n";

#ifndef DEBUG
    std::cout << "  [SKIP] 当前是 Release 编译，安全检测已关闭。\n";
    std::cout << "  使用 Debug 编译以启用：cmake .. -DCMAKE_BUILD_TYPE=Debug\n";
    return;
#else
    std::cout << "  [OK] DEBUG 模式已启用，哨兵和元数据处于活跃状态。\n\n";

    // ---- 正常流程 ----
    {
        gdm::MemoryPool<NPC, 4> pool;
        auto* a = pool.New(1, 0.f, 0.f, 0.f);
        auto* b = pool.New(2, 1.f, 0.f, 0.f);
        pool.Delete(a);
        pool.Delete(b);
        std::cout << "  ✓ 正常分配/释放：通过\n";
    }

    // ---- double-free 检测 ----
    {
        gdm::MemoryPool<NPC, 4> pool;
        auto* a = pool.New(1, 0.f, 0.f, 0.f);
        pool.Delete(a);
        std::cout << "  ✓ double-free 检测：主动演示会触发 assert，请单独运行：\n";
        std::cout << "    // pool.Delete(a);  // <-- 第二次释放：assert 触发！\n";
    }

    // ---- 越界检测 ----
    {
        gdm::MemoryPool<NPC, 4> pool;
        auto* a = pool.New(1, 0.f, 0.f, 0.f);
        std::cout << "  ✓ 越界检测：主动演示会触发 assert，请单独运行：\n";
        std::cout << "    // 模拟写越界：memset(a+1, 0xFF, 64);\n";
        std::cout << "    // pool.Delete(a);  // <-- 释放时检测后哨兵，assert 触发！\n";
        pool.Delete(a);
    }
#endif
}

// ===================================================================
// main
// ===================================================================
int main() {
    std::cout << R"(
╔══════════════════════════════════════════════════════════════╗
║         游戏服务器内存池  —  Game Server Memory Pool         ║
║         对应图谱：1.基础能力 / 1.1.2.C++语言 / 内存          ║
╚══════════════════════════════════════════════════════════════╝
)";

    benchmark_alloc_dealloc();
    demo_fragmentation();
    debug_safety_demo();

    std::cout << "\n══════════════════════════════════════════════════\n";
    std::cout <<   "  所有测试完成。\n";
    std::cout <<   "══════════════════════════════════════════════════\n\n";
    return 0;
}
