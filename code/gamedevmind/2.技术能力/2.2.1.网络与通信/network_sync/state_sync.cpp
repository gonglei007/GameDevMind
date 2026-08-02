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
 *   - 伺服校正: 服务器状态到达后，"回弹"到权威位置
 *   - 模拟网络延迟: 服务器响应滞后 3 帧
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
};

// ============================================================
// 权威服务器
// ============================================================
class AuthoritativeServer {
public:
    double pos_x = 0.0, pos_y = 0.0;
    int    server_frame = 0;
    
    // 客户端发来的命令队列
    std::deque<MoveCommand> cmd_queue;
    
    // 逐帧推进服务器
    void tick() {
        // 处理此帧之前到达的所有命令
        while (!cmd_queue.empty() && cmd_queue.front().frame_sent < server_frame) {
            auto& cmd = cmd_queue.front();
            pos_x += cmd.dx * SERVER_SPEED * DELTA_TIME;
            pos_y += cmd.dy * SERVER_SPEED * DELTA_TIME;
            cmd_queue.pop_front();
        }
        server_frame++;
    }
    
    // 获取当前权威状态快照
    ServerState get_state() const {
        return {server_frame, pos_x, pos_y};
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
        if (dx == 0.0 && dy == 0.0) {
            // 无输入, 仅推进帧
            client_frame++;
            return;
        }
        
        // --- 客户端预测: 立即移动 ---
        pred_x += dx * CLIENT_SPEED * DELTA_TIME;
        pred_y += dy * CLIENT_SPEED * DELTA_TIME;
        
        // 记录待确认命令
        pending.push_back({client_frame, dx, dy});
        client_frame++;
    }
    
    // 收到服务器状态 → 校正
    bool receive_server_state(const ServerState& ss) {
        // 清除比服务器更旧的已确认命令
        while (!pending.empty() && pending.front().frame <= ss.frame) {
            // 应用服务器速度重新计算这条命令的移动量
            auto& cmd = pending.front();
            confirmed_x += cmd.dx * SERVER_SPEED * DELTA_TIME;
            confirmed_y += cmd.dy * SERVER_SPEED * DELTA_TIME;
            pending.pop_front();
        }
        
        // 检测预测偏差
        double error_x = pred_x - confirmed_x;
        double error_y = pred_y - confirmed_y;
        double error_mag = std::sqrt(error_x * error_x + error_y * error_y);
        
        if (error_mag > 0.01) {
            // --- 回弹/校正 ---
            CorrectionEvent ev{client_frame, pred_x, pred_y, confirmed_x, confirmed_y};
            corrections.push_back(ev);
            
            // 快照到权威位置
            pred_x = confirmed_x;
            pred_y = confirmed_y;
            
            // 重新预测所有未确认的命令 (基于新的起点)
            for (auto& cmd : pending) {
                pred_x += cmd.dx * CLIENT_SPEED * DELTA_TIME;
                pred_y += cmd.dy * CLIENT_SPEED * DELTA_TIME;
            }
        } else {
            confirmed_x = pred_x;
            confirmed_y = pred_y;
        }
        
        return error_mag > 0.01; // 返回是否发生了校正
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
    std::cout << "  ║  权威位置: (" << std::setw(6) << ev.to_x
              << ", " << std::setw(6) << ev.to_y << ")      ║\n";
    double delta = ev.from_x - ev.to_x;
    std::cout << "  ║  偏差:     " << std::setw(9) << delta << "  ← 回弹量  ║\n";
    std::cout << "  ╚══════════════════════════════════════╝\n";
}

// ============================================================
// 主函数
// ============================================================
int main() {
    std::cout << "╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║    状态同步 (State Sync) 模拟 — 客户端预测+服务器校正  ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    std::cout << "▸ 场景设定:\n";
    std::cout << "  玩家持续向右移动 (输入: →)\n";
    std::cout << "  客户端预测速度: " << CLIENT_SPEED << " 单位/秒 (立即响应)\n";
    std::cout << "  服务器权威速度: " << SERVER_SPEED << " 单位/秒 (较慢, 模拟摩擦/校验)\n";
    std::cout << "  网络延迟:       " << LATENCY_FRAMES << " 帧 (" << LATENCY_FRAMES * DELTA_TIME << "秒)\n";
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
    std::cout << "  3. 伺服校正:   服务器状态到达后，修正偏差→\"回弹\"效果\n";
    std::cout << "  4. 延迟补偿:   高延迟下预测误差大，回弹更明显\n";
    std::cout << "  5. 适用场景:   FPS、MMO (玩家少但需要实时响应)\n";
    std::cout << "  6. 反作弊:     服务器校验每次移动的合法性\n";
    
    return 0;
}
