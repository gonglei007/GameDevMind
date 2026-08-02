#include "hex_coord.hpp"
#include "hex_grid.hpp"
#include "astar.hpp"

#include <iostream>
#include <iomanip>
#include <random>
#include <string>
#include <unordered_set>
#include <vector>

// ============================================================================
// ANSI 颜色
// ============================================================================
namespace color {
    const char* RESET   = "\033[0m";
    const char* BOLD    = "\033[1m";
    const char* RED     = "\033[31m";
    const char* GREEN   = "\033[32m";
    const char* YELLOW  = "\033[33m";
    const char* BLUE    = "\033[34m";
    const char* MAGENTA = "\033[35m";
    const char* CYAN    = "\033[36m";
    const char* WHITE   = "\033[37m";
    const char* GRAY    = "\033[90m";
    const char* B_RED   = "\033[91m";
    const char* B_GREEN = "\033[92m";
    const char* B_YELLOW= "\033[93m";
    const char* B_BLUE  = "\033[94m";
    const char* B_CYAN  = "\033[96m";
} // namespace color

// ============================================================================
// 地形 → 显示字符 + 颜色
// ============================================================================
struct TerrainStyle {
    std::string ch;
    const char* clr;
};

TerrainStyle terrain_style(hex::Terrain t) {
    switch (t) {
        case hex::Terrain::Plain:    return {"·", color::GREEN};
        case hex::Terrain::Mountain: return {"▲", color::YELLOW};
        case hex::Terrain::Water:    return {"≈", color::BLUE};
    }
    return {"?", color::RED};
}

// ============================================================================
// ASCII 六边形网格渲染
// ============================================================================
class HexRenderer {
public:
    HexRenderer(int cols, int rows)
        : cols_(cols), rows_(rows)
    {
        // 计算画布尺寸
        // 每个 hex 宽5字符, 水平步长4
        // 奇数行偏移2字符
        canvas_w_ = cols_ * 4 + 4;
        canvas_h_ = rows_ * 3;
        canvas_.assign(canvas_h_, std::string(canvas_w_, ' '));
        color_.assign(canvas_h_, std::vector<const char*>(canvas_w_, nullptr));
    }

    /// 在画布上放置一个六边形
    void place_hex(int col, int row, const std::string& terrain_ch,
                   const char* clr, bool is_path = false, bool is_start = false,
                   bool is_end = false)
    {
        int bx = col * 4 + (row % 2) * 2;  // 奇数行右移2
        int by = row * 3;

        const char* ch_ptr = terrain_ch.c_str();
        const char* use_clr = clr;

        if (is_path)  use_clr = color::B_RED;
        if (is_start) { use_clr = color::B_CYAN; ch_ptr = "S"; }
        if (is_end)   { use_clr = color::B_CYAN; ch_ptr = "E"; }

        // 绘制六边形边框
        // Line 0:  " ___ "
        draw(by+0, bx+1, '_', color::GRAY); draw(by+0, bx+2, '_', color::GRAY); draw(by+0, bx+3, '_', color::GRAY);
        // Line 1:  "/ T \"
        draw(by+1, bx+0, '/', color::GRAY);
        draw_str(by+1, bx+2, ch_ptr, use_clr);
        draw(by+1, bx+4, '\\', color::GRAY);
        // Line 2:  "\___/"
        draw(by+2, bx+0, '\\', color::GRAY);
        draw(by+2, bx+1, '_', color::GRAY); draw(by+2, bx+2, '_', color::GRAY); draw(by+2, bx+3, '_', color::GRAY);
        draw(by+2, bx+4, '/', color::GRAY);
    }

    /// 输出画布
    void print() const {
        for (int y = 0; y < canvas_h_; ++y) {
            for (int x = 0; x < canvas_w_; ++x) {
                if (color_[y][x])
                    std::cout << color_[y][x];
                std::cout << canvas_[y][x];
            }
            std::cout << color::RESET << '\n';
        }
    }

private:
    void draw(int y, int x, char c, const char* clr) {
        if (y >= 0 && y < canvas_h_ && x >= 0 && x < canvas_w_) {
            canvas_[y][x] = c;
            color_[y][x] = clr;
        }
    }
    void draw_str(int y, int x, const char* s, const char* clr) {
        for (int i = 0; s[i]; ++i)
            draw(y, x + i, s[i], clr);
    }

    int cols_, rows_;
    int canvas_w_, canvas_h_;
    std::vector<std::string> canvas_;
    std::vector<std::vector<const char*>> color_;
};

// ============================================================================
// 地图生成
// ============================================================================
hex::HexGrid generate_map(int cols, int rows, unsigned seed = 42) {
    hex::HexGrid grid(cols, rows);
    std::mt19937 rng(seed);

    // 地形权重: 平原60% 山地25% 水域15%
    std::discrete_distribution<int> terrain_dist({60, 25, 15});

    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            int t = terrain_dist(rng);
            hex::Terrain terrain;
            switch (t) {
                case 0: terrain = hex::Terrain::Plain;    break;
                case 1: terrain = hex::Terrain::Mountain; break;
                default: terrain = hex::Terrain::Water;   break;
            }
            grid.set_terrain({c, r}, terrain);
        }
    }
    return grid;
}

// ============================================================================
// 主程序
// ============================================================================
int main() {
    constexpr int COLS = 12;
    constexpr int ROWS = 10;

    // ---- 生成地图 ---------------------------------------------------------
    auto grid = generate_map(COLS, ROWS, 42);

    // ---- 确保起点/终点可通行 -----------------------------------------------
    hex::Offset start{1, 1};
    hex::Offset goal{10, 8};

    // 强制设为平原 (演示用)
    grid.set_terrain(start, hex::Terrain::Plain);
    grid.set_terrain(goal, hex::Terrain::Plain);

    // ---- A* 寻路 ---------------------------------------------------------
    // is_goal
    auto is_goal = [&](const hex::Offset& o) { return o == goal; };

    // get_neighbors: 返回可达邻居及移动代价
    auto get_neighbors = [&](const hex::Offset& o) {
        return grid.passable_neighbors(o);
    };

    // heuristic: 六边形距离
    auto heuristic = [](const hex::Offset& a, const hex::Offset& b) {
        return hex::hex_distance(a, b);
    };

    auto result = astar::find_path<hex::Offset, int>(
        start, is_goal, get_neighbors, heuristic);

    // ---- 构建路径集 (用于标记) ---------------------------------------------
    std::unordered_set<hex::Offset> path_set;
    for (auto& node : result.path)
        path_set.insert(node);

    // ---- ASCII 可视化 ----------------------------------------------------
    std::cout << color::BOLD
              << "\n╔══════════════════════════════════════════════════╗\n"
              << "║       六边形网格 A* 寻路 — ASCII 可视化          ║\n"
              << "╚══════════════════════════════════════════════════╝"
              << color::RESET << "\n\n";

    // 图例
    std::cout << "  图例:  ";
    std::cout << color::GREEN  << "· 平原(1)  " << color::RESET;
    std::cout << color::YELLOW << "▲ 山地(3)  " << color::RESET;
    std::cout << color::BLUE   << "≈ 水域(阻挡)" << color::RESET;
    std::cout << color::B_CYAN << "  S 起点 / E 终点  " << color::RESET;
    std::cout << color::B_RED  << "● 路径" << color::RESET;
    std::cout << "\n\n";

    // 渲染
    HexRenderer renderer(COLS, ROWS);
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            hex::Offset pos{c, r};
            auto t = grid.terrain(pos);
            auto style = terrain_style(t);

            bool is_path   = path_set.count(pos) > 0;
            bool is_start  = (pos == start);
            bool is_end    = (pos == goal);

            renderer.place_hex(c, r, style.ch, style.clr, is_path, is_start, is_end);
        }
    }
    renderer.print();

    // ---- 寻路结果 --------------------------------------------------------
    std::cout << "\n" << color::BOLD
              << "━━━━━━━━━━━━━━━━━ 寻路结果 ━━━━━━━━━━━━━━━━━\n"
              << color::RESET;

    if (result.found) {
        std::cout << color::B_GREEN << "  ✓ 找到路径!" << color::RESET << "\n";
        std::cout << "  路径长度: " << result.path.size() << " 格\n";
        std::cout << "  总代价:   " << result.cost << "\n";

        std::cout << "\n  路径详情 (Offset → 地形 → 代价):\n";
        int step = 0;
        int cumulative = 0;
        for (auto& node : result.path) {
            auto t = grid.terrain(node);
            auto style = terrain_style(t);
            int cost = hex::terrain_cost(t);
            cumulative += cost;
            std::cout << "    " << std::setw(2) << step++ << ". ("
                      << std::setw(2) << node.col << "," << std::setw(2) << node.row
                      << ")  " << style.clr << style.ch << color::RESET
                      << "  代价:" << cost
                      << "  累计:" << cumulative << "\n";
        }
    } else {
        std::cout << color::RED << "  ✗ 无法到达终点! (被水域阻挡)" << color::RESET << "\n";
    }

    // ---- 坐标转换演示 ----------------------------------------------------
    std::cout << "\n" << color::BOLD
              << "━━━━━━━━━━━━━━ 坐标转换示例 ━━━━━━━━━━━━━━\n"
              << color::RESET;

    hex::Offset demo_off{5, 3};
    auto demo_axial = hex::offset_to_axial(demo_off);
    auto demo_cube  = hex::offset_to_cube(demo_off);
    auto back_off   = hex::axial_to_offset(demo_axial);

    std::cout << "  (col,row) = (" << demo_off.col << "," << demo_off.row << ")\n";
    std::cout << "  → Axial(q,r) = (" << demo_axial.q << "," << demo_axial.r << ")\n";
    std::cout << "  → Cube(q,r,s) = (" << demo_cube.q << "," << demo_cube.r << "," << demo_cube.s << ")\n";
    std::cout << "  → 往返 Offset(col,row) = (" << back_off.col << "," << back_off.row << ")\n";

    auto neighbors = hex::hex_neighbors(demo_off);
    std::cout << "  邻居: ";
    for (auto& n : neighbors)
        std::cout << "(" << n.col << "," << n.row << ") ";
    std::cout << "\n";

    std::cout << color::GRAY << "  距离 (2,1)→(7,4) = "
              << hex::hex_distance(hex::Offset{2,1}, hex::Offset{7,4})
              << color::RESET << "\n\n";

    return 0;
}
