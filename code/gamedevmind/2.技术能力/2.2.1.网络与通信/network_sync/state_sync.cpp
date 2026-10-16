/**
 * state_sync.cpp — 状态同步(State Sync)模拟演示
 * ==============================================
 * 
 * 核心概念:
 *   服务器维护权威游戏状态，客户端发送输入，
 *   服务器处理后回传状态，客户端据此渲染。
 *   为降低感知延迟，客户端做本地预测 + 服务器校正。
 * 
 * 本演示:
 *   - 服务器权威: 服务器状态是唯一真相源
 *   - 客户端预测: 输入后立即移动，不等服务器确认
 *   - 预测校正: 采用服务器快照并重放未确认输入
 *   - 模拟管道延迟: 双向各 3 个逻辑步，不是真实 RTT 测量
 * 
 * 编译: g++ -std=c++17 -O2 state_sync.cpp -o state_sync
 * 运行: ./state_sync
 */

#include <iostream>
#include <iomanip>
#include <deque>
#include <vector>
#include <string>
#include <cmath>
#include <stdexcept>

// ============================================================
// 模拟参数
// ============================================================
constexpr double DELTA_TIME      = 0.1;    // 每帧时间 (秒)
constexpr double CLIENT_SPEED    = 1.0;    // 客户端预测速度 (单位/秒)
constexpr double SERVER_SPEED    = 0.70;   // 服务器权威速度 (比客户端慢→产生分歧)
constexpr int    LATENCY_FRAMES  = 3;      // 网络延迟 (帧数)
constexpr int    TOTAL_FRAMES    = 20;     // 总模拟帧数

// ============================================================
// 框架数据定义
// ============================================================
// 客户端发出的输入命令
struct MoveCommand {
    int   frame_sent;    // 发出时的客户端帧号
    int   player_id;
    double dx, dy;       // 移动方向 (归一化)
};

// 服务器回传的权威状态
struct ServerState {
    int   frame;         // 服务器帧号
    double pos_x, pos_y; // 权威位置
    int last_processed_input; // 已执行输入前缀的末尾；不能由服务器帧号推导
};

// ============================================================
// 权威服务器
// ============================================================
class AuthoritativeServer {
public:
    double pos_x = 0.0, pos_y = 0.0;
    int    server_frame = 0;
    int    last_processed_input = -1;
    
    // 客户端发来的命令队列
    std::deque<MoveCommand> cmd_queue;
    
    // 逐帧推进服务器
    void tick() {
        // 处理此帧之前到达的所有命令
        while (!cmd_queue.empty()) {
            const auto cmd = cmd_queue.front();
            cmd_queue.pop_front();
            if (cmd.frame_sent <= last_processed_input) continue; // 重复输入不重复执行
            // 本演示输入通道可靠有序；生产协议须另外定义缺口恢复与超时策略。
            if (cmd.frame_sent != last_processed_input + 1) {
                throw std::runtime_error("input sequence gap");
            }
            pos_x += cmd.dx * SERVER_SPEED * DELTA_TIME;
            pos_y += cmd.dy * SERVER_SPEED * DELTA_TIME;
            last_processed_input = cmd.frame_sent;
        }
        server_frame++;
    }
    
    // 获取当前权威状态快照
    ServerState get_state() const {
        return {server_frame, pos_x, pos_y, last_processed_input};
    }
};

// ============================================================
// 客户端 (带预测与校正)
// ============================================================
class PredictedClient {
public:
    // 本地预测位置 (立即响应输入)
    double pred_x = 0.0, pred_y = 0.0;
    // 上次确认的服务器位置
    double confirmed_x = 0.0, confirmed_y = 0.0;
    int    client_frame = 0;
    int    last_snapshot_frame = -1;
    int    last_processed_input = -1;
    
    // 已发出但尚未确认的命令 (用于校正回滚)
    struct PendingCommand {
        int    frame;
        double dx, dy;
    };
    std::deque<PendingCommand> pending;
    
    // 校正历史 (记录回弹事件)
    struct CorrectionEvent {
        int    frame;
        double from_x, from_y;
        double to_x, to_y;
    };
    std::vector<CorrectionEvent> corrections;
    
    // 客户端每帧: 读取输入→立即预测→发送命令
    void apply_input(double dx, double dy) {
        // 停止移动也产生有序的零输入，不能跳过它的序号。
        // --- 客户端预测: 立即移动 ---
        pred_x += dx * CLIENT_SPEED * DELTA_TIME;
        pred_y += dy * CLIENT_SPEED * DELTA_TIME;
        
        // 记录待确认命令
        pending.push_back({client_frame, dx, dy});
        client_frame++;
    }
    
    // 收到服务器状态 → 校正
    bool receive_server_state(const ServerState& ss) {
        // 本演示每服务器帧恰好产生一个快照，因此 frame 同时可用于快照新旧判断。
        // 它仍然不等于输入确认号。生产协议还需定义独立快照 ID、会话世代和序号回绕。
        if (ss.frame <= last_snapshot_frame || ss.last_processed_input < last_processed_input) return false;
        if (ss.last_processed_input < -1 || ss.last_processed_input >= client_frame) {
            throw std::runtime_error("snapshot acknowledges an input that was never sent");
        }
        while (!pending.empty() && pending.front().frame <= ss.last_processed_input) {
            pending.pop_front();
        }
        // 权威坐标来自快照，不能在客户端用 SERVER_SPEED 猜测它。
        confirmed_x = ss.pos_x;
        confirmed_y = ss.pos_y;
        double rebuilt_x = confirmed_x;
        double rebuilt_y = confirmed_y;
        for (const auto& cmd : pending) {
            rebuilt_x += cmd.dx * CLIENT_SPEED * DELTA_TIME;
            rebuilt_y += cmd.dy * CLIENT_SPEED * DELTA_TIME;
        }
        // 比较校正前后同一当前输入进度的预测，不拿当前预测与过去的权威位置直接相减。
        double error_x = pred_x - rebuilt_x;
        double error_y = pred_y - rebuilt_y;
        double error_mag = std::sqrt(error_x * error_x + error_y * error_y);
        if (error_mag > 1e-9) {
            CorrectionEvent ev{client_frame, pred_x, pred_y, rebuilt_x, rebuilt_y};
            corrections.push_back(ev);
        }
        pred_x = rebuilt_x;
        pred_y = rebuilt_y;
        last_snapshot_frame = ss.frame;
        last_processed_input = ss.last_processed_input;
        return error_mag > 1e-9;
    }
};

// ============================================================
// 可视化输出
// ============================================================
void print_correction_event(const PredictedClient::CorrectionEvent& ev) {
    std::cout << "\n  ╔══════════════════════════════════════╗\n";
    std::cout << "  ║  ⚡ 回弹事件!  帧#" << std::setw(2) << ev.frame 
              << "                    ║\n";
    std::cout << "  ╠══════════════════════════════════════╣\n";
    std::cout << "  ║  预测位置: (" << std::fixed << std::setw(6) << std::setprecision(2) << ev.from_x
              << ", " << std::setw(6) << ev.from_y << ")      ║\n";
    std::cout << "  ║  重建预测: (" << std::setw(6) << ev.to_x
              << ", " << std::setw(6) << ev.to_y << ")      ║\n";
    double delta = ev.from_x - ev.to_x;
    std::cout << "  ║  偏差:     " << std::setw(9) << delta << "  ← 回弹量  ║\n";
    std::cout << "  ╚══════════════════════════════════════╝\n";
}

// ============================================================
// 主函数
// ============================================================
int run_demo() {
    std::cout << "╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║    状态同步 (State Sync) 模拟 — 客户端预测+服务器校正  ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    std::cout << "▸ 场景设定:\n";
    std::cout << "  玩家持续向右移动 (输入: →)\n";
    std::cout << "  客户端预测速度: " << CLIENT_SPEED << " 单位/秒 (立即响应)\n";
    std::cout << "  服务器权威速度: " << SERVER_SPEED << " 单位/秒 (较慢, 模拟摩擦/校验)\n";
    std::cout << "  单向管道延迟:   " << LATENCY_FRAMES << " 步 (逻辑时长 " << LATENCY_FRAMES * DELTA_TIME << "秒)\n";
    std::cout << "  总帧数:         " << TOTAL_FRAMES << "\n\n";
    
    // ---------- 创建服务器与客户端 ----------
    AuthoritativeServer server;
    PredictedClient     client;
    
    // 延迟管道: 记录发出帧号 + 数据
    struct DelayedCmd { int sent_frame; MoveCommand cmd; };
    struct DelayedState { int sent_frame; ServerState state; };
    std::deque<DelayedCmd>   net_to_server;
    std::deque<DelayedState> net_to_client;
    
    // 预定义输入: 一直向右移动
    const double input_dx = 1.0, input_dy = 0.0;
    
    std::cout << "═══════════════════════════════════════════════════════════\n";
    std::cout << "  帧   客户端预测         服务器权威        状态\n";
    std::cout << "═══════════════════════════════════════════════════════════\n";
    
    for (int f = 0; f < TOTAL_FRAMES; ++f) {
        // ---- ① 服务器推进 ----
        server.tick();
        ServerState ss = server.get_state();
        
        // ---- ② 客户端推进 ----
        // 客户端先收到(延迟到达的)服务器状态 → 校正
        bool corrected = false;
        while (!net_to_client.empty() && f - net_to_client.front().sent_frame >= LATENCY_FRAMES) {
            corrected |= client.receive_server_state(net_to_client.front().state);
            net_to_client.pop_front();
        }
        
        // 客户端应用输入 → 立即预测
        client.apply_input(input_dx, input_dy);
        
        // 客户端发出命令 → 进网络管道 (带发出帧号)
        MoveCommand cmd{f, 0, input_dx, input_dy};
        net_to_server.push_back({f, cmd});
        
        // ---- ③ 网络传输模拟 (双向延迟 LATENCY_FRAMES 帧) ----
        // 命令: 客户端→服务器 (延迟到达)
        while (!net_to_server.empty() && f - net_to_server.front().sent_frame >= LATENCY_FRAMES) {
            server.cmd_queue.push_back(net_to_server.front().cmd);
            net_to_server.pop_front();
        }
        
        // 状态: 服务器→客户端 (延迟到达)
        net_to_client.push_back({f, ss});
        
        // ---- ④ 可视化输出 ----
        std::cout << "  " << std::setw(3) << f << "  "
                  << "预测:(" << std::fixed << std::setprecision(2) << std::setw(5) << client.pred_x
                  << "," << std::setw(5) << client.pred_y << ")   "
                  << "权威:(" << std::setw(5) << ss.pos_x
                  << "," << std::setw(5) << ss.pos_y << ")   ";
        
        if (corrected) {
            std::cout << "⚡回弹!";
        } else {
            std::cout << "✓正常";
        }
        std::cout << "\n";
    }
    
    // 停止产生输入，并排空在途输入与确认；此时才检查终态收敛。
    for (int f = TOTAL_FRAMES; f < TOTAL_FRAMES + 2 * LATENCY_FRAMES + 4; ++f) {
        server.tick();
        while (!net_to_client.empty() && f - net_to_client.front().sent_frame >= LATENCY_FRAMES) {
            client.receive_server_state(net_to_client.front().state);
            net_to_client.pop_front();
        }
        while (!net_to_server.empty() && f - net_to_server.front().sent_frame >= LATENCY_FRAMES) {
            server.cmd_queue.push_back(net_to_server.front().cmd);
            net_to_server.pop_front();
        }
        net_to_client.push_back({f, server.get_state()});
        if (client.last_processed_input == TOTAL_FRAMES - 1) break;
    }

    // ---------- 汇总回弹事件 ----------
    std::cout << "\n═══════════════════════════════════════════════════════════\n";
    std::cout << "  校正/回弹事件汇总\n";
    std::cout << "═══════════════════════════════════════════════════════════\n";
    
    if (client.corrections.empty()) {
        std::cout << "  无回弹事件 (预测与服务器一致)\n";
    }
    
    for (auto& ev : client.corrections) {
        print_correction_event(ev);
    }
    
    // ---------- 总结 ----------
    std::cout << "\n═══════════════════════════════════════════════════════════\n";
    std::cout << "  最终位置\n";
    std::cout << "═══════════════════════════════════════════════════════════\n\n";
    
    std::cout << "  服务器权威位置: (" << std::fixed << std::setprecision(2)
              << server.pos_x << ", " << server.pos_y << ")\n";
    std::cout << "  客户端最终预测: (" << client.pred_x << ", " << client.pred_y << ")\n";
    
    double final_error = std::abs(client.pred_x - server.pos_x);
    std::cout << "  最终偏差: " << final_error << "\n\n";
    
    std::cout << "▸ 状态同步关键要点:\n";
    std::cout << "  1. 服务器权威: 服务器状态是唯一真相源 (Source of Truth)\n";
    std::cout << "  2. 客户端预测: 输入后立即移动，减少感知延迟\n";
    std::cout << "  3. 输入确认:   按 last_processed_input 移除输入，再从快照重放\n";
    std::cout << "  4. 校正幅度:   比较重建后的当前预测；本演示未实现显示层平滑\n";
    std::cout << "  5. 选型依据:   确定性、权威、交互与资源预算，不按游戏类型硬套\n";
    std::cout << "  6. 验证边界:   本地有序延迟模拟，未实现真实传输与反作弊校验\n";

    const bool converged = client.pending.empty() && net_to_server.empty() && server.cmd_queue.empty()
        && client.last_processed_input == TOTAL_FRAMES - 1
        && std::hypot(client.pred_x - server.pos_x, client.pred_y - server.pos_y) < 1e-9;
    std::cout << (converged ? "PASS: drained inputs converge\n" : "FAIL: inputs did not converge\n");
    return converged ? 0 : 1;
}

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void run_regressions() {
    PredictedClient client;
    client.apply_input(1.0, 0.0); // input 0
    client.apply_input(1.0, 0.0); // input 1
    client.receive_server_state({100, 42.0, -3.0, -1});
    require(client.pending.size() == 2, "server tick was mistaken for an input ack");
    require(std::abs(client.pred_x - 42.2) < 1e-9 && client.pred_y == -3.0,
            "authoritative coordinates were not used before replay");

    client.receive_server_state({101, 7.0, 0.0, 0});
    require(client.pending.size() == 1 && client.pending.front().frame == 1,
            "partial ack removed an unacknowledged input");
    require(std::abs(client.pred_x - 7.1) < 1e-9, "unacknowledged input was not replayed");
    const double predicted = client.pred_x;
    require(!client.receive_server_state({101, -999.0, 0.0, 0}), "duplicate snapshot was accepted");
    require(!client.receive_server_state({99, -999.0, 0.0, 0}), "old snapshot was accepted");
    require(!client.receive_server_state({102, -999.0, 0.0, -1}), "input ack regressed");
    require(client.pred_x == predicted && client.pending.size() == 1, "stale snapshot changed client state");

    bool rejected = false;
    try { client.receive_server_state({102, 0.0, 0.0, 2}); }
    catch (const std::runtime_error&) { rejected = true; }
    require(rejected && client.pending.size() == 1 && client.last_snapshot_frame == 101,
            "future ack was not rejected before mutating state");
    client.receive_server_state({102, 8.0, 0.0, 1});
    require(client.pending.empty() && client.pred_x == 8.0, "full ack did not converge");

    // With identical rules there is no correction merely because the snapshot is from the past.
    PredictedClient matching;
    matching.apply_input(1.0, 0.0);
    matching.apply_input(1.0, 0.0);
    require(!matching.receive_server_state({100, 0.1, 0.0, 0}), "matching prediction was unnecessarily corrected");
    matching.apply_input(0.0, 0.0); // input 2 is a stop, not a missing sequence number
    require(matching.pending.size() == 2 && matching.pending.back().frame == 2, "stop input was not retained");
    matching.receive_server_state({101, 0.2, 0.0, 2});
    require(matching.pending.empty() && std::abs(matching.pred_x - 0.2) < 1e-9, "stop ack did not converge");

    AuthoritativeServer server;
    server.cmd_queue.push_back({0, 0, 1.0, 0.0});
    server.cmd_queue.push_back({0, 0, 1.0, 0.0}); // duplicate
    server.cmd_queue.push_back({1, 0, 1.0, 0.0});
    server.tick();
    require(server.last_processed_input == 1 && std::abs(server.pos_x - 0.14) < 1e-9,
            "server applied a duplicate input or reported an incorrect ack");
    std::cout << "PASS: authoritative snapshot, input acks, stale packets, stop and duplicate input\n";
}

int main(int argc, char* argv[]) {
    try {
        run_regressions();
        if (argc == 2 && std::string(argv[1]) == "--self-test") return 0;
        if (argc != 1) throw std::runtime_error("usage: state_sync [--self-test]");
        return run_demo();
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
