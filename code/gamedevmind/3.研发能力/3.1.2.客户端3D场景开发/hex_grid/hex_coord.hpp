#pragma once

#include <array>
#include <cmath>
#include <cstdlib>
#include <vector>

// ============================================================================
// 六边形坐标系统
//
// 三种坐标表示:
//   Cube  (q, r, s)  约束: q + r + s = 0
//   Axial (q, r)     等同于 Cube 丢掉 s
//   Offset(col, row) 错行偏移, 采用 odd-r (奇数行右移)
//
// 邻居方向 (Axial):
//        (+1, 0)  (右上)
//   (0,+1)  ●  (+1,-1)
//        ( 0, 0)        ← 六边形自身
//   (-1,+1)  ●  (0,-1)
//        (-1, 0)  (左下)
//
// 6个邻居 (q,r):
//   (+1, 0), (+1,-1), (0,-1), (-1, 0), (-1,+1), (0,+1)
// ============================================================================

namespace hex {

// ---- 基础类型 ---------------------------------------------------------------
struct Cube {
    int q, r, s;
    Cube(int q_ = 0, int r_ = 0, int s_ = 0) : q(q_), r(r_), s(s_) {}
    bool operator==(const Cube& o) const { return q == o.q && r == o.r && s == o.s; }
};

struct Axial {
    int q, r;
    Axial(int q_ = 0, int r_ = 0) : q(q_), r(r_) {}
    bool operator==(const Axial& o) const { return q == o.q && r == o.r; }
};

struct Offset {
    int col, row;  // odd-r: 奇数行右移半格
    Offset(int c = 0, int r = 0) : col(c), row(r) {}
    bool operator==(const Offset& o) const { return col == o.col && row == o.row; }
};

// ---- 转换函数 ---------------------------------------------------------------
inline Cube axial_to_cube(Axial a) {
    return {a.q, a.r, -a.q - a.r};
}
inline Axial cube_to_axial(Cube c) {
    return {c.q, c.r};
}
inline Cube offset_to_cube(Offset o) {
    // odd-r → cube
    int q = o.col - (o.row - (o.row & 1)) / 2;
    int r = o.row;
    return {q, r, -q - r};
}
inline Offset cube_to_offset(Cube c) {
    // cube → odd-r
    int col = c.q + (c.r - (c.r & 1)) / 2;
    int row = c.r;
    return {col, row};
}
inline Axial offset_to_axial(Offset o) {
    return cube_to_axial(offset_to_cube(o));
}
inline Offset axial_to_offset(Axial a) {
    return cube_to_offset(axial_to_cube(a));
}

// ---- 距离 ------------------------------------------------------------------
/// 六边形网格上的曼哈顿距离 (Cube坐标)
inline int hex_distance(Cube a, Cube b) {
    return (std::abs(a.q - b.q) + std::abs(a.r - b.r) + std::abs(a.s - b.s)) / 2;
}
inline int hex_distance(Axial a, Axial b) {
    return hex_distance(axial_to_cube(a), axial_to_cube(b));
}
inline int hex_distance(Offset a, Offset b) {
    return hex_distance(offset_to_cube(a), offset_to_cube(b));
}

// ---- 邻居 ------------------------------------------------------------------
/// 返回 Axial 坐标的6个邻居 (顺序: 右, 右上, 左上, 左, 左下, 右下)
inline std::array<Axial, 6> hex_neighbors(Axial a) {
    // 6个方向的 (dq, dr)
    static constexpr int dirs[6][2] = {
        {+1,  0}, {+1, -1}, { 0, -1},
        {-1,  0}, {-1, +1}, { 0, +1}
    };
    std::array<Axial, 6> result;
    for (int i = 0; i < 6; ++i)
        result[i] = {a.q + dirs[i][0], a.r + dirs[i][1]};
    return result;
}

inline std::array<Cube, 6> hex_neighbors(Cube c) {
    auto an = hex_neighbors(cube_to_axial(c));
    std::array<Cube, 6> result;
    for (int i = 0; i < 6; ++i)
        result[i] = axial_to_cube(an[i]);
    return result;
}

inline std::array<Offset, 6> hex_neighbors(Offset o) {
    auto an = hex_neighbors(offset_to_axial(o));
    std::array<Offset, 6> result;
    for (int i = 0; i < 6; ++i)
        result[i] = axial_to_offset(an[i]);
    return result;
}

} // namespace hex

// ---- std::hash 支持 (用于 unordered_map / unordered_set) ---------------------
namespace std {
template <> struct hash<hex::Axial> {
    size_t operator()(const hex::Axial& a) const noexcept {
        return (size_t)a.q * 0x9e3779b9 + (size_t)a.r;
    }
};
template <> struct hash<hex::Offset> {
    size_t operator()(const hex::Offset& o) const noexcept {
        return (size_t)o.col * 0x9e3779b9 + (size_t)o.row;
    }
};
template <> struct hash<hex::Cube> {
    size_t operator()(const hex::Cube& c) const noexcept {
        return (size_t)c.q * 0x9e3779b9 + (size_t)c.r;
    }
};
} // namespace std
