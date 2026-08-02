// ============================================================
// main.cpp — 对象池模式演示：子弹系统性能对比
// ============================================================
// 场景模拟：
//   射击游戏中，每帧生成大量子弹（Bullet），飞行一段时间后回收。
//   对比两种策略：
//     A) 直接 new/delete — 传统方式
//     B) 对象池 Acquire/Release — 优化方式
//   统计耗时差异，直观展示对象池的性能优势。
// ============================================================

#include "object_pool.hpp"
#include <chrono>
#include <cmath>
#include <iostream>
#include <random>
#include <vector>

// ============================================================
// Bullet — 子弹对象（模拟游戏中的子弹）
// ============================================================
struct Bullet {
    float pos_x = 0.0f;
    float pos_y = 0.0f;
    float vel_x = 0.0f;
    float vel_y = 0.0f;
    float lifetime = 0.0f; // 剩余生命周期（秒）
    bool  active  = false;

    // 重置为"新子弹"状态（对象池复用时调用）
    void Reset() {
        pos_x = pos_y = 0.0f;
        vel_x = vel_y = 0.0f;
        lifetime = 0.0f;
        active  = false;
    }

    // 初始化子弹参数
    void Init(float x, float y, float vx, float vy, float life) {
        pos_x = x; pos_y = y;
        vel_x = vx; vel_y = vy;
        lifetime = life;
        active  = true;
    }

    // 每帧更新（返回是否仍然存活）
    bool Update(float dt) {
        lifetime -= dt;
        if (lifetime <= 0.0f) {
            active = false;
            return false;
        }
        pos_x += vel_x * dt;
        pos_y += vel_y * dt;
        return true;
    }
};

// ============================================================
// 计时工具
// ============================================================
class Timer {
public:
    using Clock = std::chrono::high_resolution_clock;
    void Start() { start_ = Clock::now(); }
    double ElapsedMs() const {
        auto end = Clock::now();
        return std::chrono::duration<double, std::milli>(end - start_).count();
    }
private:
    Clock::time_point start_;
};

// ============================================================
// 策略 A：直接 new/delete
// ============================================================
double BenchmarkNewDelete(int frame_count, int bullets_per_frame) {
    Timer timer;
    timer.Start();

    std::vector<Bullet*> active_bullets;
    active_bullets.reserve(bullets_per_frame * 2);

    std::mt19937 rng(42); // 固定种子，可复现
    std::uniform_real_distribution<float> vel_dist(-100.0f, 100.0f);

    for (int frame = 0; frame < frame_count; ++frame) {
        // 每帧：生成 bullets_per_frame 颗子弹
        for (int i = 0; i < bullets_per_frame; ++i) {
            auto* b = new Bullet();
            b->Init(0.0f, 0.0f, vel_dist(rng), vel_dist(rng), 3.0f);
            active_bullets.push_back(b);
        }

        // 每帧：更新所有活跃子弹，回收过期子弹
        const float dt = 1.0f / 60.0f;
        for (auto it = active_bullets.begin(); it != active_bullets.end(); ) {
            if (!(*it)->Update(dt)) {
                delete *it; // 直接释放
                it = active_bullets.erase(it);
            } else {
                ++it;
            }
        }
    }

    // 清理剩余子弹
    for (auto* b : active_bullets) delete b;

    return timer.ElapsedMs();
}

// ============================================================
// 策略 B：对象池 Acquire/Release
// ============================================================
double BenchmarkObjectPool(int frame_count, int bullets_per_frame) {
    Timer timer;
    timer.Start();

    // 创建对象池：预分配 bullets_per_frame * 2（覆盖峰值）
    ObjectPool<Bullet> pool(bullets_per_frame * 2);

    std::vector<Bullet*> active_bullets;
    active_bullets.reserve(bullets_per_frame * 2);

    std::mt19937 rng(42); // 相同种子
    std::uniform_real_distribution<float> vel_dist(-100.0f, 100.0f);

    for (int frame = 0; frame < frame_count; ++frame) {
        // 每帧：从池中获取子弹
        for (int i = 0; i < bullets_per_frame; ++i) {
            auto& b = pool.Acquire();
            b.Init(0.0f, 0.0f, vel_dist(rng), vel_dist(rng), 3.0f);
            active_bullets.push_back(&b);
        }

        // 每帧：更新并回收过期子弹
        const float dt = 1.0f / 60.0f;
        for (auto it = active_bullets.begin(); it != active_bullets.end(); ) {
            if (!(*it)->Update(dt)) {
                pool.Release(**it); // 归还池中
                it = active_bullets.erase(it);
            } else {
                ++it;
            }
        }
    }

    // 归还剩余子弹
    for (auto* b : active_bullets) pool.Release(*b);

    double elapsed = timer.ElapsedMs();
    pool.PrintStats("子弹对象池");
    return elapsed;
}

// ============================================================
// main
// ============================================================
int main() {
    // 测试参数
    constexpr int kFrameCount      = 300;  // 模拟 300 帧（5 秒 @60FPS）
    constexpr int kBulletsPerFrame = 200;  // 每帧生成 200 颗子弹

    std::cout << "╔══════════════════════════════════════════════╗\n";
    std::cout << "║   对象池模式演示：子弹系统性能对比          ║\n";
    std::cout << "╚══════════════════════════════════════════════╝\n";
    std::cout << "\n测试参数：\n";
    std::cout << "  模拟帧数: " << kFrameCount << " 帧\n";
    std::cout << "  每帧子弹: " << kBulletsPerFrame << " 颗\n";
    std::cout << "  总子弹数: " << (kFrameCount * kBulletsPerFrame) << " 颗\n";

    // -------------------------------------------------------
    // 策略 A：new/delete
    // -------------------------------------------------------
    std::cout << "\n--- 策略 A: new/delete ---\n";
    double t_new = BenchmarkNewDelete(kFrameCount, kBulletsPerFrame);
    std::cout << "  耗时: " << t_new << " ms\n";

    // -------------------------------------------------------
    // 策略 B：对象池
    // -------------------------------------------------------
    std::cout << "\n--- 策略 B: 对象池 ---\n";
    double t_pool = BenchmarkObjectPool(kFrameCount, kBulletsPerFrame);
    std::cout << "  耗时: " << t_pool << " ms\n";

    // -------------------------------------------------------
    // 对比结果
    // -------------------------------------------------------
    std::cout << "\n═══════════════ 性能对比 ═══════════════\n";
    std::cout << "  new/delete : " << t_new  << " ms\n";
    std::cout << "  对象池     : " << t_pool << " ms\n";
    if (t_pool > 0) {
        std::cout << "  加速比     : " << (t_new / t_pool) << "x\n";
        std::cout << "  节省时间   : " << (t_new - t_pool) << " ms\n";
    }
    std::cout << "\n💡 结论：对象池避免频繁 malloc/free，\n"
              << "   减少内存碎片，帧率更稳定。\n";
    std::cout << "════════════════ 演示结束 ════════════════\n";

    return 0;
}
