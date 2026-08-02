// ============================================================
// quadtree.hpp — 模板化四叉树空间分区数据结构
// ============================================================
// 算法来源：Finkel & Bentley (1974) "Quad Trees"
// 游戏场景应用：
//   • 碰撞检测 — 快速找出可能碰撞的对象对，避免 O(n²) 暴力检测
//   • 视锥剔除 — 仅查询摄像机视野内的对象提交渲染
//   • 近邻查询 — 查找玩家周围的NPC/道具/可交互物体
//   • 范围攻击 — 圆形/矩形 AOE 技能命中判定
//
// 设计要点：
//   - 模板化支持任意 2D 数据类型（NPC、子弹、场景物件等）
//   - 每个节点存储 AABB（轴对齐包围盒）+ 对象 ID 列表
//   - 超过容量自动分裂为 4 个子象限，低于容量自动合并
//   - 最大深度限制防止无限递归（默认 8 层）
// ============================================================

#pragma once

#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <functional>
#include <memory>
#include <type_traits>
#include <vector>

// ============================================================
// 基础几何类型 — 不依赖任何第三方库
// ============================================================

/// @brief 2D 向量
template <typename T>
struct Vec2 {
    T x{}, y{};

    Vec2() = default;
    Vec2(T x, T y) : x(x), y(y) {}

    Vec2 operator+(const Vec2& o) const { return {x + o.x, y + o.y}; }
    Vec2 operator-(const Vec2& o) const { return {x - o.x, y - o.y}; }
    Vec2 operator*(T s)          const { return {x * s, y * s}; }

    /// 曼哈顿距离（用于快速估算）
    T ManhattanDist(const Vec2& o) const {
        return std::abs(x - o.x) + std::abs(y - o.y);
    }
};

/// @brief 轴对齐包围盒 (Axis-Aligned Bounding Box)
///   用 中心点 + 半宽度 表示，内存紧凑且查询高效
template <typename T>
struct AABB {
    Vec2<T> center;   // 矩形中心点（世界坐标）
    Vec2<T> half;     // 半宽、半高（从中心到边界的距离）

    AABB() = default;
    AABB(const Vec2<T>& c, const Vec2<T>& h) : center(c), half(h) {}

    // ---- 边界查询 ----
    T Left()   const { return center.x - half.x; }
    T Right()  const { return center.x + half.x; }
    T Bottom() const { return center.y - half.y; }
    T Top()    const { return center.y + half.y; }

    /// @brief 判断两个 AABB 是否重叠（碰撞检测核心）
    ///   分离轴定理（SAT）在 AABB 上的简化形式
    bool Overlaps(const AABB& o) const {
        return std::abs(center.x - o.center.x) <= (half.x + o.half.x) &&
               std::abs(center.y - o.center.y) <= (half.y + o.half.y);
    }

    /// @brief 判断当前 AABB 是否完全包含另一个 AABB
    bool Contains(const AABB& o) const {
        return Left()   <= o.Left()   && Right()  >= o.Right() &&
               Bottom() <= o.Bottom() && Top()    >= o.Top();
    }

    /// @brief 判断一个点是否在 AABB 内
    bool ContainsPoint(const Vec2<T>& p) const {
        return p.x >= Left()  && p.x <= Right() &&
               p.y >= Bottom() && p.y <= Top();
    }
};

// ============================================================
// 四叉树节点
// ============================================================

/// @brief 四叉树象限索引
enum class Quadrant : uint8_t {
    NW = 0,  // 左上 (North-West):  x < center.x, y >= center.y
    NE = 1,  // 右上 (North-East): x >= center.x, y >= center.y
    SW = 2,  // 左下 (South-West): x < center.x,  y <  center.y
    SE = 3,  // 右下 (South-East): x >= center.x, y <  center.y
};

/// @brief 四叉树内部节点
///
/// 分裂示意（每个节点划分为 4 个象限）：
///
///        ┌────────┬────────┐
///        │  NW    │  NE    │
///        │ (0)    │ (1)    │
///        ├────────┼────────┤
///        │  SW    │  SE    │
///        │ (2)    │ (3)    │
///        └────────┴────────┘
///
/// 对象存储在能完全包含它的最小节点中。
template <typename T, typename IDType = int>
class Quadtree {
public:
    /// 节点配置常量
    static constexpr int kDefaultMaxDepth    = 8;   // 最大深度限制（根为 0）
    static constexpr int kDefaultMaxObjects  = 4;   // 分裂阈值：超过此数量触发分裂
    static constexpr int kMergeThreshold     = 2;   // 合并阈值：低于此数量尝试合并子节点

    /// 存储的对象条目：包围盒 + 数据 ID
    struct Entry {
        AABB<T>   bounds;   // 对象的 AABB
        IDType    id;       // 外部数据 ID（如实体句柄）
    };

    // ---- 构造 & 析构 ----

    /// @brief 构造四叉树
    /// @param region  根节点的覆盖范围（世界边界）
    /// @param maxDepth  最大递归深度
    /// @param maxObjectsPerNode  节点分裂前可容纳的最大对象数
    Quadtree(const AABB<T>& region,
             int maxDepth          = kDefaultMaxDepth,
             int maxObjectsPerNode = kDefaultMaxObjects)
        : m_region(region)
        , m_maxDepth(maxDepth)
        , m_maxObjects(maxObjectsPerNode)
        , m_depth(0)
    {}

    // ---- 主要操作 ----

    /// @brief 插入一个对象到四叉树
    /// @param bounds  对象的包围盒
    /// @param id      对象的唯一标识
    /// @return true 成功插入，false 对象超出根节点范围
    bool Insert(const AABB<T>& bounds, IDType id) {
        return InsertImpl(bounds, id);
    }

    /// @brief 查询与给定范围相交的所有对象 ID
    /// @param range    查询范围（AABB 或圆的外接矩形）
    /// @param outIDs   输出：命中对象的 ID 列表（不清空，追加模式）
    void Query(const AABB<T>& range, std::vector<IDType>& outIDs) const {
        QueryImpl(range, outIDs);
    }

    /// @brief 查询与给定范围相交的所有对象（含包围盒），用于碰撞检测
    /// @param range     查询范围
    /// @param outEntries 输出：命中的 Entry 列表
    void QueryEntries(const AABB<T>& range, std::vector<Entry>& outEntries) const {
        QueryEntriesImpl(range, outEntries);
    }

    /// @brief 清空四叉树（保留根节点结构，清除所有对象和子树）
    void Clear() {
        m_objects.clear();
        m_children.fill(nullptr);
    }

    /// @brief 获取四叉树中所有对象
    void GetAllEntries(std::vector<Entry>& outEntries) const {
        outEntries.insert(outEntries.end(), m_objects.begin(), m_objects.end());
        for (auto& child : m_children) {
            if (child) child->GetAllEntries(outEntries);
        }
    }

    // ---- 属性访问 ----
    const AABB<T>& GetRegion() const { return m_region; }
    int GetDepth()          const { return m_depth;  }
    size_t ObjectCount()    const { return m_objects.size(); }
    bool IsLeaf()           const {
        return m_children[0] == nullptr;  // 四子节点同时创建/销毁
    }

    // ---- 遍历（供调试/可视化使用）----

    /// @brief 获取子节点数组的只读访问（供遍历统计用）
    const std::array<std::unique_ptr<Quadtree>, 4>& GetChildren() const {
        return m_children;
    }

    /// @brief 深度优先遍历整棵树（先根本节点，再递归子节点）
    template <typename Visitor>
    void Visit(Visitor&& visitor) {
        visitor(*this);
        for (auto& child : m_children) {
            if (child) child->Visit(std::forward<Visitor>(visitor));
        }
    }

private:
    // ---- 内部实现 ----

    /// 确定对象所属的象限
    /// 规则：对象可以跨象限边界——此时它留在当前节点而不下放
    int GetQuadrant(const AABB<T>& bounds) const {
        // 检查对象是否完全位于某个象限内
        bool left  = bounds.Right()  < m_region.center.x;
        bool right = bounds.Left()   > m_region.center.x;
        bool top    = bounds.Bottom() > m_region.center.y;
        bool bottom = bounds.Top()    < m_region.center.y;

        // 如果跨了中心线，返回 -1 表示留在当前节点
        if ((!left && !right) || (!top && !bottom))
            return -1;

        if (top)    return left ? static_cast<int>(Quadrant::NW) : static_cast<int>(Quadrant::NE);
        else        return left ? static_cast<int>(Quadrant::SW) : static_cast<int>(Quadrant::SE);
    }

    /// 创建子节点（分裂）
    void Split() {
        assert(IsLeaf() && "Split called on non-leaf node");

        const T hw = m_region.half.x * T(0.5);  // 子节点半宽
        const T hh = m_region.half.y * T(0.5);  // 子节点半高
        const Vec2<T>& c = m_region.center;

        // 4 个子节点的包围盒
        m_children[static_cast<int>(Quadrant::NW)] = std::make_unique<Quadtree>(
            AABB<T>{Vec2<T>{c.x - hw, c.y + hh}, Vec2<T>{hw, hh}},
            m_maxDepth, m_maxObjects, m_depth + 1);
        m_children[static_cast<int>(Quadrant::NE)] = std::make_unique<Quadtree>(
            AABB<T>{Vec2<T>{c.x + hw, c.y + hh}, Vec2<T>{hw, hh}},
            m_maxDepth, m_maxObjects, m_depth + 1);
        m_children[static_cast<int>(Quadrant::SW)] = std::make_unique<Quadtree>(
            AABB<T>{Vec2<T>{c.x - hw, c.y - hh}, Vec2<T>{hw, hh}},
            m_maxDepth, m_maxObjects, m_depth + 1);
        m_children[static_cast<int>(Quadrant::SE)] = std::make_unique<Quadtree>(
            AABB<T>{Vec2<T>{c.x + hw, c.y - hh}, Vec2<T>{hw, hh}},
            m_maxDepth, m_maxObjects, m_depth + 1);

        // 重新分配当前节点的对象到子节点（能完全放入某个子象限的才下放）
        std::vector<Entry> retained;
        for (auto& obj : m_objects) {
            int q = GetQuadrant(obj.bounds);
            if (q >= 0) {
                m_children[q]->Insert(obj.bounds, obj.id);
            } else {
                retained.push_back(obj);  // 跨边界的对象留在当前层
            }
        }
        m_objects = std::move(retained);
    }

    /// 尝试合并子节点（当子节点的对象总数低于阈值时）
    void TryMerge() {
        if (IsLeaf()) return;

        // 汇总所有子孙对象
        size_t totalObjects = m_objects.size();
        for (auto& child : m_children) {
            if (!child->IsLeaf()) return;  // 存在非叶子的孙子节点，不合并
            totalObjects += child->m_objects.size();
        }

        // 低于合并阈值则将所有子节点对象提升到当前节点
        if (totalObjects <= static_cast<size_t>(m_maxObjects)) {
            for (auto& child : m_children) {
                m_objects.insert(m_objects.end(),
                                 child->m_objects.begin(),
                                 child->m_objects.end());
                child->m_objects.clear();
            }
            m_children.fill(nullptr);  // 销毁子树
        }
    }

    /// 递归插入实现
    bool InsertImpl(const AABB<T>& bounds, IDType id) {
        // 边界检查：对象必须与当前节点区域相交
        if (!m_region.Overlaps(bounds)) return false;

        // 情况 1: 当前是叶子节点，且未达到容量上限或已达最大深度 → 直接存储
        if (IsLeaf()) {
            m_objects.push_back({bounds, id});

            // 如果超过容量且未到最大深度，则分裂
            if (m_objects.size() > static_cast<size_t>(m_maxObjects) &&
                m_depth < m_maxDepth) {
                Split();
            }
            return true;
        }

        // 情况 2: 非叶子节点 → 尝试下放到子节点
        int q = GetQuadrant(bounds);
        if (q >= 0) {
            // 对象完全在某个子象限内，递归插入
            m_children[q]->InsertImpl(bounds, id);
        } else {
            // 跨边界的对象留在当前节点
            m_objects.push_back({bounds, id});
        }
        return true;
    }

    /// 递归查询实现
    void QueryImpl(const AABB<T>& range, std::vector<IDType>& outIDs) const {
        // 剪枝：如果查询范围与当前节点不相交，直接返回
        if (!m_region.Overlaps(range)) return;

        // 检查当前节点的所有对象
        for (auto& obj : m_objects) {
            if (obj.bounds.Overlaps(range)) {
                outIDs.push_back(obj.id);
            }
        }

        // 如果不是叶子节点，递归查询子节点
        if (!IsLeaf()) {
            for (auto& child : m_children) {
                child->QueryImpl(range, outIDs);
            }
        }
    }

    /// 递归查询（返回完整 Entry）
    void QueryEntriesImpl(const AABB<T>& range, std::vector<Entry>& out) const {
        if (!m_region.Overlaps(range)) return;

        for (auto& obj : m_objects) {
            if (obj.bounds.Overlaps(range)) {
                out.push_back(obj);
            }
        }

        if (!IsLeaf()) {
            for (auto& child : m_children) {
                child->QueryEntriesImpl(range, out);
            }
        }
    }

    // ---- 私有构造（子节点创建用）----
    Quadtree(const AABB<T>& region, int maxDepth, int maxObjects, int depth)
        : m_region(region)
        , m_maxDepth(maxDepth)
        , m_maxObjects(maxObjects)
        , m_depth(depth)
    {}

    // ---- 数据成员 ----
    AABB<T>                               m_region;   // 本节点覆盖的空间范围
    int                                   m_maxDepth;
    int                                   m_maxObjects;
    int                                   m_depth;    // 当前深度（根=0）
    std::vector<Entry>                    m_objects;  // 存储在本节点的对象
    std::array<std::unique_ptr<Quadtree>, 4> m_children; // NW/NE/SW/SE
};

// ============================================================
// 四叉树辅助工具：碰撞检测器
// ============================================================

/// @brief 四叉树辅助函数：批量碰撞检测
///   使用四叉树为每个对象查询附近可能的碰撞对，然后仅对这些候选对做精确检测
///
/// @param objects      所有待检测对象的包围盒和 ID
/// @param treeRegion   四叉树覆盖的世界范围（应包含所有 objects）
/// @param outPairs     输出：(idA, idB) 碰撞对，保证 idA < idB 避免重复
template <typename T, typename IDType>
void QuadtreeCollisionCheck(
    const std::vector<typename Quadtree<T, IDType>::Entry>& objects,
    const AABB<T>& treeRegion,
    std::vector<std::pair<IDType, IDType>>& outPairs)
{
    // 如果对象太少，直接暴力检测
    if (objects.size() < 10) {
        for (size_t i = 0; i < objects.size(); ++i) {
            for (size_t j = i + 1; j < objects.size(); ++j) {
                if (objects[i].bounds.Overlaps(objects[j].bounds)) {
                    outPairs.emplace_back(objects[i].id, objects[j].id);
                }
            }
        }
        return;
    }

    // 构建四叉树
    Quadtree<T, IDType> tree(treeRegion);
    for (auto& obj : objects) {
        tree.Insert(obj.bounds, obj.id);
    }

    // 对每个对象，在四叉树中查询可能碰撞的候选
    // 使用 ID 比较避免重复检测 (idA, idB) 和 (idB, idA)
    for (auto& obj : objects) {
        std::vector<typename Quadtree<T, IDType>::Entry> candidates;
        tree.QueryEntries(obj.bounds, candidates);

        for (auto& cand : candidates) {
            if (cand.id <= obj.id) continue;  // 仅记录单向，避免重复

            // 精确 AABB 重叠检测（已在 Query 时筛选，这里做最后确认）
            if (obj.bounds.Overlaps(cand.bounds)) {
                outPairs.emplace_back(obj.id, cand.id);
            }
        }
    }
}

/// @brief 暴力 O(n²) 碰撞检测 — 用于验证四叉树结果正确性
template <typename T, typename IDType>
void BruteForceCollisionCheck(
    const std::vector<typename Quadtree<T, IDType>::Entry>& objects,
    std::vector<std::pair<IDType, IDType>>& outPairs)
{
    for (size_t i = 0; i < objects.size(); ++i) {
        for (size_t j = i + 1; j < objects.size(); ++j) {
            if (objects[i].bounds.Overlaps(objects[j].bounds)) {
                outPairs.emplace_back(objects[i].id, objects[j].id);
            }
        }
    }
}
