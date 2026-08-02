// ============================================================
// main.cpp — 四叉树 vs 暴力 O(n²) 碰撞检测性能对比
// ============================================================
// 测试场景：
//   模拟游戏中 500 个对象（NPC + 子弹 + 道具）随机分布在 2000×2000 的世界中，
//   分别用四叉树空间分区和暴力 O(n²) 做碰撞检测，对比性能。
//
// 预期结果：
//   • 四叉树：O(n log n) 级别，500 对象 ~数百微秒
//   • 暴力法：O(n²) 级别，500 对象需要 ~125K 次 AABB 检测
//   • 两种方法碰撞对数量一致（验证正确性）
//   • 对象越稀疏，四叉树优势越明显
// ============================================================

#include "quadtree.hpp"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

// ============================================================
// 游戏场景配置
// ============================================================

/// 世界尺寸：2000 × 2000 单位（典型的 2D 俯视角游戏地图）
constexpr float kWorldSize = 2000.0f;

/// 测试对象数量
constexpr int kObjectCount = 500;

/// NPC 半宽（大约 1 个角色的碰撞体积，宽 40 × 高 40）
constexpr float kNpcHalfW = 20.0f;
constexpr float kNpcHalfH = 20.0f;

/// 子弹半宽（细长或点状，宽 5 × 高 5 的快速飞行物）
constexpr float kBulletHalfW = 5.0f;
constexpr float kBulletHalfH = 5.0f;

/// 道具半宽（中等大小，宽 15 × 高 15 的掉落物/宝箱等）
constexpr float kItemHalfW = 15.0f;
constexpr float kItemHalfH = 15.0f;

// ============================================================
// 辅助函数
// ============================================================

/// @brief 简单的高精度计时器（微秒）
class Timer {
public:
    using Clock = std::chrono::high_resolution_clock;
    using Us    = std::chrono::microseconds;

    void Start() { m_start = Clock::now(); }
    int64_t ElapsedUs() const {
        return std::chrono::duration_cast<Us>(Clock::now() - m_start).count();
    }

private:
    Clock::time_point m_start;
};

/// @brief 打印分隔线
void PrintSeparator(const std::string& title = "") {
    std::cout << "\n";
    if (!title.empty()) {
        std::cout << "┌" << std::string(58, '─') << "┐\n";
        std::cout << "│ " << std::left << std::setw(57) << title << "│\n";
        std::cout << "└" << std::string(58, '─') << "┘\n";
    } else {
        std::cout << std::string(60, '─') << "\n";
    }
}

/// @brief 生成模拟游戏对象
///
/// 场景模拟：
///   • 60% NPC — 散布在地图各处，可重叠（不考虑寻路碰撞）
///   • 25% 子弹 — 密集飞行在 NPC 活跃区域
///   • 15% 道具 — 离散分布
///
/// 使用固定种子保证结果可复现。
std::vector<Quadtree<float>::Entry> GenerateGameObjects(int count) {
    std::mt19937 rng(42);  // 固定种子，结果可复现
    std::uniform_real_distribution<float> posDist(0.0f, kWorldSize);
    std::uniform_real_distribution<float> nudge(-5.0f, 5.0f);

    std::vector<Quadtree<float>::Entry> objects;
    objects.reserve(count);

    for (int i = 0; i < count; ++i) {
        float hw, hh;
        const char* type;

        if (i < count * 0.60) {
            // NPC：较大的碰撞体积
            hw = kNpcHalfW;  hh = kNpcHalfH;
            type = "NPC";
        } else if (i < count * 0.85) {
            // 子弹：小体积，散布在 NPC 可能出现的位置
            hw = kBulletHalfW; hh = kBulletHalfH;
            type = "Bullet";
        } else {
            // 道具：中等体积
            hw = kItemHalfW;  hh = kItemHalfH;
            type = "Item";
        }

        // 生成位置：让一部分对象聚集产生碰撞
        float cx = posDist(rng);
        float cy = posDist(rng);

        // 让约 40% 的对象聚集在 (1000, 1000) 附近（模拟城镇/战场中心）
        if (i > count * 0.6) {
            cx = 1000.0f + nudge(rng) * 30.0f;
            cy = 1000.0f + nudge(rng) * 30.0f;
        }

        objects.push_back({
            AABB<float>{Vec2<float>{cx, cy}, Vec2<float>{hw, hh}},
            static_cast<int>(i)  // ID 就是索引
        });
    }

    return objects;
}

/// @brief 排序并去重碰撞对（统一输出格式用）
void NormalizePairs(std::vector<std::pair<int, int>>& pairs) {
    for (auto& p : pairs) {
        if (p.first > p.second) std::swap(p.first, p.second);
    }
    std::sort(pairs.begin(), pairs.end());
    auto last = std::unique(pairs.begin(), pairs.end());
    pairs.erase(last, pairs.end());
}

/// @brief 递归计算四叉树的统计信息
template <typename T, typename IDType>
void GatherTreeStats(const Quadtree<T, IDType>& node,
                     int& totalNodes, int& maxDepth, int& maxObjectsPerNode,
                     int& totalObjects) {
    totalNodes++;
    maxDepth = std::max(maxDepth, node.GetDepth());

    size_t objCount = node.ObjectCount();
    totalObjects += static_cast<int>(objCount);
    maxObjectsPerNode = std::max(maxObjectsPerNode, static_cast<int>(objCount));

    if (!node.IsLeaf()) {
        // 访问子节点 — 通过 const_cast 绕过 const（仅供统计用）
        // 更好的做法是提供 const 遍历接口，但这里简化处理
        const auto& children = reinterpret_cast<const std::array<
            std::unique_ptr<Quadtree<T, IDType>>, 4>&>(node);
        for (auto& child : children) {
            if (child) GatherTreeStats(*child, totalNodes, maxDepth, maxObjectsPerNode, totalObjects);
        }
    }
}

// 前向声明（避免交叉引用问题，使用简单的 Visit 模式接口）
// 直接在 main 中实现统计

// ============================================================
// 主函数
// ============================================================

int main() {
    std::cout << R"(
╔══════════════════════════════════════════════════════════════╗
║     四叉树空间分区 — 游戏碰撞检测性能对比                    ║
║     Quadtree vs. Brute-Force O(n²) Benchmark                ║
╚══════════════════════════════════════════════════════════════╝
)";

    // -----------------------------------------------------------
    // 1. 生成测试数据（模拟游戏场景）
    // -----------------------------------------------------------
    PrintSeparator("1. 生成模拟游戏对象");
    auto objects = GenerateGameObjects(kObjectCount);
    std::cout << "   生成 " << objects.size() << " 个对象：\n";
    std::cout << "     • NPC   × " << static_cast<int>(kObjectCount * 0.60) << " (碰撞体积 40×40)\n";
    std::cout << "     • 子弹  × " << static_cast<int>(kObjectCount * 0.25) << " (碰撞体积 10×10)\n";
    std::cout << "     • 道具  × " << static_cast<int>(kObjectCount * 0.15) << " (碰撞体积 30×30)\n";
    std::cout << "   世界范围: " << kWorldSize << "×" << kWorldSize << " 单位\n";

    // -----------------------------------------------------------
    // 2. 四叉树构建 & 碰撞检测
    // -----------------------------------------------------------
    PrintSeparator("2. 四叉树碰撞检测");

    // 四叉树根节点覆盖整个世界
    AABB<float> worldBounds{Vec2<float>{kWorldSize * 0.5f, kWorldSize * 0.5f},
                            Vec2<float>{kWorldSize * 0.5f, kWorldSize * 0.5f}};

    Timer timer;
    std::vector<std::pair<int, int>> quadtreePairs;

    timer.Start();
    QuadtreeCollisionCheck<float, int>(objects, worldBounds, quadtreePairs);
    int64_t quadtreeUs = timer.ElapsedUs();

    NormalizePairs(quadtreePairs);

    std::cout << "   四叉树碰撞检测完成：\n";
    std::cout << "   ├─ 耗时: " << std::setw(8) << quadtreeUs << " µs\n";
    std::cout << "   └─ 碰撞对: " << quadtreePairs.size() << " 对\n";

    // -----------------------------------------------------------
    // 3. 暴力 O(n²) 碰撞检测（对照）
    // -----------------------------------------------------------
    PrintSeparator("3. 暴力 O(n²) 碰撞检测（对照）");

    std::vector<std::pair<int, int>> brutePairs;
    timer.Start();
    BruteForceCollisionCheck<float, int>(objects, brutePairs);
    int64_t bruteUs = timer.ElapsedUs();

    NormalizePairs(brutePairs);

    std::cout << "   暴力碰撞检测完成：\n";
    std::cout << "   ├─ 耗时: " << std::setw(8) << bruteUs << " µs\n";
    std::cout << "   │   (执行了 " << (objects.size() * (objects.size() - 1) / 2) << " 次 AABB 检测)\n";
    std::cout << "   └─ 碰撞对: " << brutePairs.size() << " 对\n";

    // -----------------------------------------------------------
    // 4. 结果验证 & 性能分析
    // -----------------------------------------------------------
    PrintSeparator("4. 结果验证 & 性能分析");

    // 验证正确性：两种方法结果必须完全一致
    bool correct = (quadtreePairs == brutePairs);
    if (correct) {
        std::cout << "   ✅ 正确性验证通过！两方法碰撞对完全一致。\n";
    } else {
        std::cout << "   ❌ 正确性验证失败！\n";
        std::cout << "      四叉树结果: " << quadtreePairs.size() << " 对\n";
        std::cout << "      暴力法结果: " << brutePairs.size() << " 对\n";

        // 找出差异
        std::vector<std::pair<int, int>> diff;
        std::set_difference(
            brutePairs.begin(), brutePairs.end(),
            quadtreePairs.begin(), quadtreePairs.end(),
            std::back_inserter(diff));
        std::cout << "      差异（暴力有而四叉树无）: " << diff.size() << " 对\n";
    }

    // 性能对比
    double speedup = static_cast<double>(bruteUs) / std::max(quadtreeUs, 1L);
    std::cout << "\n   ⚡ 性能对比：\n";
    std::cout << "   ├─ 四叉树: " << std::setw(8) << quadtreeUs << " µs\n";
    std::cout << "   ├─ 暴力法: " << std::setw(8) << bruteUs  << " µs\n";
    std::cout << "   ├─ 加速比: " << std::fixed << std::setprecision(1) << speedup << "×\n";
    std::cout << "   └─ 节省:   " << std::setw(6) << std::setprecision(1)
              << (1.0 - 1.0 / speedup) * 100.0 << "% 的时间\n";

    // -----------------------------------------------------------
    // 5. 四叉树结构分析
    // -----------------------------------------------------------
    PrintSeparator("5. 四叉树结构分析");

    // 构建一棵用于统计的四叉树
    Quadtree<float, int> statsTree(worldBounds, 8, 4);
    for (auto& obj : objects) {
        statsTree.Insert(obj.bounds, obj.id);
    }

    // 遍历收集统计信息
    int totalNodes = 0, maxDepthSeen = 0, maxObjPerNode = 0, totalObjSlots = 0;

    std::function<void(const Quadtree<float, int>&)> gatherStats =
        [&](const Quadtree<float, int>& node) {
            totalNodes++;
            maxDepthSeen = std::max(maxDepthSeen, node.GetDepth());
            int objCount = static_cast<int>(node.ObjectCount());
            totalObjSlots += objCount;
            maxObjPerNode = std::max(maxObjPerNode, objCount);

            for (auto& child : node.GetChildren()) {
                if (child) gatherStats(*child);
            }
        };
    gatherStats(statsTree);

    std::cout << "   树的统计信息：\n";
    std::cout << "   ├─ 节点总数: " << totalNodes << "\n";
    std::cout << "   ├─ 最大深度: " << maxDepthSeen << " / 8\n";
    std::cout << "   ├─ 每节点最多对象: " << maxObjPerNode << " / 4\n";
    std::cout << "   ├─ 对象槽位总计: " << totalObjSlots << " (含内部节点跨边界对象)\n";
    std::cout << "   └─ 对比: 暴力法需要 " << (kObjectCount * (kObjectCount - 1) / 2)
              << " 次 AABB 检测\n";

    // -----------------------------------------------------------
    // 6. 不同规模下的扩展测试
    // -----------------------------------------------------------
    PrintSeparator("6. 不同规模扩展测试");

    std::vector<int> testSizes = {100, 500, 1000, 2000};
    std::cout << "   " << std::left << std::setw(10) << "对象数"
              << std::setw(14) << "四叉树(µs)"
              << std::setw(14) << "暴力法(µs)"
              << std::setw(10) << "加速比"
              << "碰撞对\n";
    std::cout << "   " << std::string(60, '─') << "\n";

    for (int n : testSizes) {
        // 对每种规模生成数据（用不同种子偏移但保持分布一致）
        std::mt19937 rngN(42 + n);
        std::uniform_real_distribution<float> posDistN(0.0f, kWorldSize);
        std::uniform_real_distribution<float> nudgeN(-5.0f, 5.0f);

        std::vector<Quadtree<float>::Entry> objs;
        objs.reserve(n);
        for (int i = 0; i < n; ++i) {
            float hw = (i % 3 == 0) ? kNpcHalfW : ((i % 3 == 1) ? kBulletHalfW : kItemHalfW);
            float hh = (i % 3 == 0) ? kNpcHalfH : ((i % 3 == 1) ? kBulletHalfH : kItemHalfH);
            float cx = posDistN(rngN);
            float cy = posDistN(rngN);
            if (i > n * 0.6) {
                cx = 1000.0f + nudgeN(rngN) * 30.0f;
                cy = 1000.0f + nudgeN(rngN) * 30.0f;
            }
            objs.push_back({
                AABB<float>{Vec2<float>{cx, cy}, Vec2<float>{hw, hh}},
                i
            });
        }

        std::vector<std::pair<int, int>> qtPairs, bfPairs;

        timer.Start();
        QuadtreeCollisionCheck<float, int>(objs, worldBounds, qtPairs);
        int64_t qtUs = timer.ElapsedUs();

        timer.Start();
        BruteForceCollisionCheck<float, int>(objs, bfPairs);
        int64_t bfUs = timer.ElapsedUs();

        NormalizePairs(qtPairs);
        NormalizePairs(bfPairs);

        double spd = static_cast<double>(bfUs) / std::max(qtUs, 1L);

        std::cout << "   " << std::left << std::setw(10) << n
                  << std::right << std::setw(12) << qtUs << " "
                  << std::setw(12) << bfUs << " "
                  << std::setw(8) << std::fixed << std::setprecision(1) << spd << "×"
                  << "  " << qtPairs.size() << "\n";
    }

    // -----------------------------------------------------------
    // 7. 典型游戏场景演示
    // -----------------------------------------------------------
    PrintSeparator("7. 游戏场景演示：范围查询（视锥剔除模拟）");

    // 模拟摄像机视锥：玩家在 (1000, 1000)，视野范围 400×300
    AABB<float> cameraView{Vec2<float>{1000.0f, 1000.0f}, Vec2<float>{200.0f, 150.0f}};

    Quadtree<float, int> gameTree(worldBounds, 8, 4);
    for (auto& obj : objects) {
        gameTree.Insert(obj.bounds, obj.id);
    }

    std::vector<int> visibleIDs;
    timer.Start();
    gameTree.Query(cameraView, visibleIDs);
    int64_t queryUs = timer.ElapsedUs();

    std::cout << "   摄像机位置: (1000, 1000)，视野 400×300\n";
    std::cout << "   视锥查询结果:\n";
    std::cout << "   ├─ 可见对象: " << visibleIDs.size() << " / " << kObjectCount << "\n";
    std::cout << "   ├─ 查询耗时: " << queryUs << " µs\n";
    std::cout << "   └─ 剪枝率:   " << std::fixed << std::setprecision(1)
              << (1.0 - static_cast<double>(visibleIDs.size()) / kObjectCount) * 100.0 << "%\n";

    std::cout << "\n   如果每帧都要做视锥剔除（60 FPS）:\n";
    std::cout << "   └─ 单帧查询 " << queryUs << " µs = "
              << std::fixed << std::setprecision(2) << queryUs / 1000.0 << " ms"
              << "（远小于 16.6ms 的帧预算）\n";

    // -----------------------------------------------------------
    // 完成
    // -----------------------------------------------------------
    PrintSeparator();
    std::cout << "   🎮 演示完成。四叉树是 2D 空间分区的核心数据结构。\n";
    std::cout << "   在 3D 游戏中使用八叉树 (Octree)，原理完全相同。\n\n";

    return correct ? 0 : 1;
}
