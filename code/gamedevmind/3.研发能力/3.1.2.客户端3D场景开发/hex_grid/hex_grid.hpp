#pragma once

#include "hex_coord.hpp"
#include <unordered_map>
#include <vector>

namespace hex {

// ============================================================================
// 地形类型 & 移动代价
// ============================================================================
enum class Terrain : int {
    Plain    = 1,   // 平原 — 代价 1
    Mountain = 3,   // 山地 — 代价 3
    Water    = 99   // 水域 — 不可通行 (阻挡)
};

/// 返回该地形的移动代价; 水域返回 -1 表示阻挡
inline int terrain_cost(Terrain t) {
    switch (t) {
        case Terrain::Plain:    return 1;
        case Terrain::Mountain: return 3;
        case Terrain::Water:    return -1;  // 阻挡
    }
    return -1;
}

inline bool is_blocked(Terrain t) { return t == Terrain::Water; }

// ============================================================================
// 六边形网格
// ============================================================================
class HexGrid {
public:
    HexGrid(int cols, int rows)
        : cols_(cols), rows_(rows) {}

    /// 设置指定 Offset 坐标的地形
    void set_terrain(Offset o, Terrain t) {
        cells_[o] = t;
    }

    /// 读取地形; 越界视为水域(阻挡)
    Terrain terrain(Offset o) const {
        auto it = cells_.find(o);
        if (it != cells_.end()) return it->second;
        return Terrain::Water;  // 边界外阻挡
    }

    /// 移动代价; -1 表示不可通行
    int move_cost(Offset o) const {
        return terrain_cost(terrain(o));
    }

    bool is_passable(Offset o) const {
        return !is_blocked(terrain(o));
    }

    /// 获取可达邻居及其移动代价
    /// 返回 vector<pair<Offset, cost>>
    std::vector<std::pair<Offset, int>> passable_neighbors(Offset o) const {
        std::vector<std::pair<Offset, int>> result;
        for (auto& nb : hex_neighbors(o)) {
            int cost = move_cost(nb);
            if (cost > 0) {
                result.emplace_back(nb, cost);
            }
        }
        return result;
    }

    int cols() const { return cols_; }
    int rows() const { return rows_; }

    /// 检查坐标是否在网格范围内
    bool in_bounds(Offset o) const {
        return o.col >= 0 && o.col < cols_ && o.row >= 0 && o.row < rows_;
    }

private:
    int cols_, rows_;
    std::unordered_map<Offset, Terrain> cells_;
};

} // namespace hex
