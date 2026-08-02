/**
 * lockstep.cpp — 帧同步(Lockstep)模拟演示
 * ===========================================
 * 
 * 核心概念:
 *   帧同步要求所有客户端在每一帧执行相同的确定性逻辑，
 *   输入在所有客户端间同步，从而保证状态一致。
 * 
 * 本演示:
 *   - 两个"客户端"使用完全相同的输入序列
 *   - 各自独立运行确定性游戏逻辑
 *   - 每帧输出状态，最终对比一致性
 * 
 * 特点: 输入驱动、确定性、固定帧率、无服务器权威
 * 
 * 编译: g++ -std=c++17 -O2 lockstep.cpp -o lockstep
 * 运行: ./lockstep
 */

#include <iostream>
#include <vector>
#include <string>
#include <cstdint>    // uint64_t
#include <iomanip>    // std::setw

// ============================================================
// 游戏常量
// ============================================================
constexpr int GRID_W     = 10;   // 网格宽度
constexpr int GRID_H     = 10;   // 网格高度
constexpr int FRAME_RATE = 15;   // 固定帧率 (演示用，实际RTS常用30)
constexpr int TOTAL_FRAMES = 8;  // 总帧数

// ============================================================
// 输入定义 — 每一帧每个玩家的输入
// ============================================================
enum class Input : int {
    STAY  = 0,
    UP    = 1,
    DOWN  = 2,
    LEFT  = 3,
    RIGHT = 4
};

// 输入名称映射 (中文)
const char* input_name(Input in) {
    switch (in) {
        case Input::STAY:  return "停留";
        case Input::UP:    return "↑上";
        case Input::DOWN:  return "↓下";
        case Input::LEFT:  return "←左";
        case Input::RIGHT: return "→右";
    }
    return "??";
}

// ============================================================
// 确定性游戏状态
// ============================================================
struct GameState {
    int frame = 0;
    // 玩家坐标 (列, 行) — 左上角为(0,0)
    int px[2] = {1, 8};   // P0 出生左上, P1 出生右下
    int py[2] = {1, 8};   // (左上角为原点(0,0), y向下增长)
    
    // 用于检测一致性: 整个状态的哈希
    uint64_t hash() const {
        uint64_t h = frame;
        h = h * 31 + px[0]; h = h * 31 + py[0];
        h = h * 31 + px[1]; h = h * 31 + py[1];
        return h;
    }
    
    bool operator==(const GameState& o) const {
        return frame == o.frame && px[0] == o.px[0] && py[0] == o.py[0]
               && px[1] == o.px[1] && py[1] == o.py[1];
    }
};

// ============================================================
// 确定性游戏逻辑 — 单帧推进
// ============================================================
// 这是帧同步的核心: 同样的输入 + 同样的初始状态 = 同样的结果
// 绝对不能使用 rand()、系统时间、浮点运算等非确定性操作
GameState advance_frame(const GameState& prev, Input p0_in, Input p1_in) {
    GameState next = prev;
    next.frame = prev.frame + 1;
    
    // 处理玩家0的移动 (确定性: 使用整数运算)
    struct { int dx, dy; } dirs[] = {
        {0,0}, {0,-1}, {0,1}, {-1,0}, {1,0}  // STAY, UP, DOWN, LEFT, RIGHT
    };
    
    auto move_player = [&](int pid, Input in) {
        auto& d = dirs[static_cast<int>(in)];
        int nx = next.px[pid] + d.dx;
        int ny = next.py[pid] + d.dy;
        // 边界检查 — 确定性逻辑
        if (nx >= 0 && nx < GRID_W && ny >= 0 && ny < GRID_H) {
            next.px[pid] = nx;
            next.py[pid] = ny;
        }
    };
    
    move_player(0, p0_in);
    move_player(1, p1_in);
    
    return next;
}

// ============================================================
// 可视化: 打印网格
// ============================================================
void print_grid(const GameState& state, const std::string& label) {
    std::cout << "\n  ╔══════════════════════════════════════╗\n";
    std::cout << "  ║  " << label << "  (帧#" << std::setw(2) << state.frame << ")\n";
    std::cout << "  ╠══════════════════════════════════════╣\n";
    
    for (int y = 0; y < GRID_H; ++y) {
        std::cout << "  ║ ";
        for (int x = 0; x < GRID_W; ++x) {
            bool p0_here = (state.px[0] == x && state.py[0] == y);
            bool p1_here = (state.px[1] == x && state.py[1] == y);
            
            if (p0_here && p1_here) std::cout << "⚡";
            else if (p0_here)        std::cout << "🅐";  // P0 = A
            else if (p1_here)        std::cout << "🅑";  // P1 = B
            else                     std::cout << "· ";
        }
        std::cout << "║\n";
    }
    std::cout << "  ╚══════════════════════════════════════╝\n";
    std::cout << "  状态哈希: 0x" << std::hex << state.hash() << std::dec << "\n";
}

// ============================================================
// 帧同步客户端模拟
// ============================================================
struct LockstepClient {
    std::string   name;
    GameState     state;
    // 输入缓冲区 — 帧同步中，客户端收集所有玩家的输入后才推进
    std::vector<Input> p0_inputs;
    std::vector<Input> p1_inputs;
    
    LockstepClient(const std::string& n) : name(n) {
        state.frame = 0;
    }
    
    // 接收一帧的输入 (模拟从网络收到)
    void receive_inputs(int frame, Input p0, Input p1) {
        // 确保帧索引连续
        if (static_cast<int>(p0_inputs.size()) < frame + 1) {
            p0_inputs.resize(frame + 1, Input::STAY);
            p1_inputs.resize(frame + 1, Input::STAY);
        }
        p0_inputs[frame] = p0;
        p1_inputs[frame] = p1;
    }
    
    // 执行一帧 (仅在收到该帧所有玩家输入后才执行)
    bool try_execute_frame(int frame) {
        if (frame >= static_cast<int>(p0_inputs.size())) return false;
        state = advance_frame(state, p0_inputs[frame], p1_inputs[frame]);
        return true;
    }
};

// ============================================================
// 主函数
// ============================================================
int main() {
    std::cout << "╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║      帧同步 (Lockstep) 模拟 — 确定性状态同步           ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    // ---------- 预定义输入序列 ----------
    // 每一帧: {P0输入, P1输入}
    // 这是两个客户端都会收到的相同输入
    struct FrameInput {
        Input p0, p1;
        const char* desc;
    };
    
    std::vector<FrameInput> input_sequence = {
        {Input::RIGHT, Input::LEFT,  "P0→右  P1←左"},
        {Input::RIGHT, Input::LEFT,  "P0→右  P1←左"},
        {Input::DOWN,  Input::UP,    "P0↓下  P1↑上"},
        {Input::DOWN,  Input::UP,    "P0↓下  P1↑上"},
        {Input::RIGHT, Input::STAY,  "P0→右  P1停留"},
        {Input::DOWN,  Input::LEFT,  "P0↓下  P1←左"},
        {Input::RIGHT, Input::UP,    "P0→右  P1↑上"},
        {Input::STAY,  Input::STAY,  "双方停留"},
    };
    
    // ---------- 创建两个客户端 ----------
    LockstepClient client_a("客户端 Alpha (模拟主机)");
    LockstepClient client_b("客户端 Beta  (模拟副机)");
    
    std::cout << "▸ 初始状态\n";
    std::cout << "  两个客户端从相同的初始状态开始 (P0在左上, P1在右下)\n";
    print_grid(client_a.state, "初始状态");
    std::cout << "  ✅ 初始状态一致: " << (client_a.state == client_b.state ? "是" : "否") << "\n";
    
    // ---------- 帧同步循环 ----------
    std::cout << "\n═══════════════════════════════════════════════════════════\n";
    std::cout << "  帧同步推进 (固定帧率: " << FRAME_RATE << " FPS)\n";
    std::cout << "  关键: 两个客户端接收相同输入 → 独立计算 → 结果必然一致\n";
    std::cout << "═══════════════════════════════════════════════════════════\n";
    
    for (int f = 0; f < TOTAL_FRAMES; ++f) {
        auto& fi = input_sequence[f];
        
        std::cout << "\n┌─ 帧 #" << f << " ──────────────────────────────────────┐\n";
        std::cout << "│ 输入: " << fi.desc << "                          │\n";
        std::cout << "└────────────────────────────────────────────┘\n";
        
        // 两个客户端收到完全相同的输入
        client_a.receive_inputs(f, fi.p0, fi.p1);
        client_b.receive_inputs(f, fi.p0, fi.p1);
        
        // 各自执行确定性逻辑
        bool a_ok = client_a.try_execute_frame(f);
        bool b_ok = client_b.try_execute_frame(f);
        
        if (!a_ok || !b_ok) {
            std::cout << "  ⚠️ 帧 " << f << " 执行失败! (缺少输入)\n";
            continue;
        }
        
        // 并排展示两个客户端的状态
        std::cout << "\n  客户端 A (Alpha)                 客户端 B (Beta)\n";
        std::cout << "  ────────────────                 ────────────────\n";
        
        // 紧凑格式并排显示
        for (int y = 0; y < GRID_H; ++y) {
            std::cout << "  ";
            // 客户端 A 的该行
            for (int x = 0; x < GRID_W; ++x) {
                bool p0 = (client_a.state.px[0]==x && client_a.state.py[0]==y);
                bool p1 = (client_a.state.px[1]==x && client_a.state.py[1]==y);
                if (p0&&p1) std::cout << "⚡";
                else if(p0) std::cout << "🅐";
                else if(p1) std::cout << "🅑";
                else         std::cout << "· ";
            }
            std::cout << "          ";
            // 客户端 B 的该行
            for (int x = 0; x < GRID_W; ++x) {
                bool p0 = (client_b.state.px[0]==x && client_b.state.py[0]==y);
                bool p1 = (client_b.state.px[1]==x && client_b.state.py[1]==y);
                if (p0&&p1) std::cout << "⚡";
                else if(p0) std::cout << "🅐";
                else if(p1) std::cout << "🅑";
                else         std::cout << "· ";
            }
            std::cout << "\n";
        }
        
        // 一致性检查
        bool consistent = (client_a.state == client_b.state);
        std::cout << "  ─────────────────────────────────────────────────\n";
        std::cout << "  状态哈希 A: 0x" << std::hex << client_a.state.hash()
                  << "  B: 0x" << client_b.state.hash() << std::dec << "\n";
        std::cout << "  一致性: " << (consistent ? "✅ 一致" : "❌ 不一致!") << "\n";
    }
    
    // ---------- 最终验证 ----------
    std::cout << "\n═══════════════════════════════════════════════════════════\n";
    std::cout << "  最终验证\n";
    std::cout << "═══════════════════════════════════════════════════════════\n\n";
    
    bool final_consistent = (client_a.state == client_b.state);
    std::cout << "  客户端 A 最终状态:\n";
    std::cout << "    P0 位置: (" << client_a.state.px[0] << "," << client_a.state.py[0] << ")\n";
    std::cout << "    P1 位置: (" << client_a.state.px[1] << "," << client_a.state.py[1] << ")\n";
    std::cout << "    哈希: 0x" << std::hex << client_a.state.hash() << std::dec << "\n\n";
    
    std::cout << "  客户端 B 最终状态:\n";
    std::cout << "    P0 位置: (" << client_b.state.px[0] << "," << client_b.state.py[0] << ")\n";
    std::cout << "    P1 位置: (" << client_b.state.px[1] << "," << client_b.state.py[1] << ")\n";
    std::cout << "    哈希: 0x" << std::hex << client_b.state.hash() << std::dec << "\n\n";
    
    std::cout << "  ╔════════════════════════════════════╗\n";
    if (final_consistent) {
        std::cout << "  ║  ✅ 帧同步验证通过!              ║\n";
        std::cout << "  ║  两个客户端状态完全一致          ║\n";
    } else {
        std::cout << "  ║  ❌ 帧同步验证失败!              ║\n";
        std::cout << "  ║  两个客户端状态不一致            ║\n";
    }
    std::cout << "  ╚════════════════════════════════════╝\n\n";
    
    std::cout << "▸ 帧同步关键要点:\n";
    std::cout << "  1. 输入驱动:   所有客户端收集相同输入后统一执行\n";
    std::cout << "  2. 确定性逻辑: 相同输入+初始状态=相同输出 (无随机/系统时间)\n";
    std::cout << "  3. 固定帧率:   所有客户端以相同帧率推进 (Turn-lock)\n";
    std::cout << "  4. 无需服务器: 客户端自行计算，服务器仅转发输入\n";
    std::cout << "  5. 适用场景:   RTS、MOBA (大量单位，带宽有限)\n";
    
    return final_consistent ? 0 : 1;
}
