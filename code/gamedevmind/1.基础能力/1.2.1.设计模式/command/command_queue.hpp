#pragma once
// ============================================================
// command_queue.hpp — 命令队列：录制 / 执行 / 撤销 / 回放
// ============================================================
// 游戏场景应用：
//   - 格斗游戏：录制连招 → 回放练习
//   - RTS：录制操作序列 → 回放整局比赛
//   - 关卡编辑器：Undo/Redo 操作历史
// ============================================================

#include "command.hpp"
#include <algorithm>
#include <deque>
#include <memory>
#include <string>
#include <vector>

// -----------------------------------------------------------
// CommandQueue — 命令队列
// -----------------------------------------------------------
class CommandQueue {
public:
    CommandQueue() = default;

    // -------------------------------------------------------
    // 录制模式：将命令追加到待执行队列
    // -------------------------------------------------------
    void Record(std::unique_ptr<ICommand> cmd) {
        pending_.push_back(std::move(cmd));
        // 同时保存到"原始录制"中，供回放使用
        // 这里简单用名字保存（实际游戏应序列化完整命令）
        recorded_names_.push_back(pending_.back()->GetName());
    }

    // -------------------------------------------------------
    // 执行队列中所有待执行的命令（逐条执行并压入历史栈）
    // -------------------------------------------------------
    void ExecuteAll(Player& player) {
        std::cout << "\n[CommandQueue] 执行 " << pending_.size() << " 条命令...\n";
        for (auto& cmd : pending_) {
            std::cout << "  ▶ " << cmd->GetName() << std::endl;
            cmd->Execute(player);
            history_.push_back(std::move(cmd));
        }
        pending_.clear();
    }

    // -------------------------------------------------------
    // Undo：撤销最近 N 条命令
    // -------------------------------------------------------
    void UndoLast(Player& player, size_t count = 1) {
        count = std::min(count, history_.size());
        std::cout << "\n[CommandQueue] 撤销最近 " << count << " 条命令...\n";
        for (size_t i = 0; i < count; ++i) {
            auto cmd = std::move(history_.back());
            history_.pop_back();
            std::cout << "  ◀ Undo " << cmd->GetName() << std::endl;
            cmd->Undo(player);
            undone_.push_back(std::move(cmd));
        }
    }

    // -------------------------------------------------------
    // Redo：重做已撤销的命令
    // -------------------------------------------------------
    void RedoLast(Player& player, size_t count = 1) {
        count = std::min(count, undone_.size());
        std::cout << "\n[CommandQueue] 重做 " << count << " 条命令...\n";
        for (size_t i = 0; i < count; ++i) {
            auto cmd = std::move(undone_.back());
            undone_.pop_back();
            std::cout << "  ▶ Redo " << cmd->GetName() << std::endl;
            cmd->Execute(player);
            history_.push_back(std::move(cmd));
        }
    }

    // -------------------------------------------------------
    // 回放模式：基于录制的命令名称重新创建命令并执行
    // （实际游戏中需要完整的序列化/反序列化）
    // -------------------------------------------------------
    void Replay(Player& player) {
        std::cout << "\n[CommandQueue] 🔄 回放录制序列（共 " << recorded_names_.size()
                  << " 条）...\n";
        player = Player{player.name}; // 重置玩家状态
        for (const auto& name : recorded_names_) {
            std::cout << "  ▶ Replay: " << name << std::endl;
            // 简化：解析名字模拟执行效果
            if (name.find("Move(1,0)") != std::string::npos) {
                player.pos_x += 1;
            } else if (name.find("Move(0,1)") != std::string::npos) {
                player.pos_y += 1;
            } else if (name.find("Move(5,0)") != std::string::npos) {
                player.pos_x += 5;
            } else if (name.find("Attack") != std::string::npos) {
                // 攻击演示不做实际伤害
            } else if (name.find("Skill:Fireball") != std::string::npos) {
                player.pos_x += 10;
            }
        }
    }

    // -------------------------------------------------------
    // 查看录制序列
    // -------------------------------------------------------
    void PrintRecorded() const {
        std::cout << "录制的命令序列 (" << recorded_names_.size() << " 条):\n";
        for (size_t i = 0; i < recorded_names_.size(); ++i) {
            std::cout << "  [" << i << "] " << recorded_names_[i] << "\n";
        }
    }

    // -------------------------------------------------------
    // 清理
    // -------------------------------------------------------
    void Clear() {
        pending_.clear();
        history_.clear();
        undone_.clear();
        recorded_names_.clear();
    }

private:
    std::deque<std::unique_ptr<ICommand>> pending_;  // 待执行队列
    std::deque<std::unique_ptr<ICommand>> history_;  // 执行历史（用于 Undo）
    std::deque<std::unique_ptr<ICommand>> undone_;   // 已撤销（用于 Redo）
    std::vector<std::string> recorded_names_;         // 录制序列（用于回放）
};
