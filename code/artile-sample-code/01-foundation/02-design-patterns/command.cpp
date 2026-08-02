/**
 * 命令模式 — 游戏输入缓冲 & 回放系统
 *
 * 对应文章：一-02-设计模式实战
 *
 * 场景：格斗游戏中，玩家输入需要缓冲执行；
 * 同时所有命令可序列化用于录像回放。
 */

#include <iostream>
#include <vector>
#include <queue>
#include <memory>
#include <string>

// ============================================================
// 命令基类
// ============================================================
class Command {
public:
    virtual ~Command() = default;
    virtual void execute() = 0;
    virtual void undo() {}
    virtual std::string describe() const = 0;
};

// ============================================================
// 接收者：游戏角色
// ============================================================
class Fighter {
public:
    void jump()     { std::cout << "  🦘 跳跃！" << std::endl; }
    void punch()    { std::cout << "  👊 出拳！" << std::endl; }
    void kick()     { std::cout << "  🦶 踢腿！" << std::endl; }
    void special()  { std::cout << "  ✨ 必杀技！波动拳！" << std::endl; }
    void block()    { std::cout << "  🛡️  防御" << std::endl; }
};

// ============================================================
// 具体命令
// ============================================================
class JumpCommand : public Command {
    Fighter& f_;
public:
    explicit JumpCommand(Fighter& f) : f_(f) {}
    void execute() override { f_.jump(); }
    std::string describe() const override { return "Jump"; }
};

class PunchCommand : public Command {
    Fighter& f_;
public:
    explicit PunchCommand(Fighter& f) : f_(f) {}
    void execute() override { f_.punch(); }
    std::string describe() const override { return "Punch"; }
};

class KickCommand : public Command {
    Fighter& f_;
public:
    explicit KickCommand(Fighter& f) : f_(f) {}
    void execute() override { f_.kick(); }
    std::string describe() const override { return "Kick"; }
};

class SpecialCommand : public Command {
    Fighter& f_;
public:
    explicit SpecialCommand(Fighter& f) : f_(f) {}
    void execute() override { f_.special(); }
    std::string describe() const override { return "Special"; }
};

// ============================================================
// 输入处理器 — 命令队列（缓冲 3 帧输入）
// ============================================================
class InputHandler {
public:
    void enqueue(std::unique_ptr<Command> cmd) {
        buffer_.push(std::move(cmd));
    }

    void processFrame() {
        if (buffer_.empty()) { return; }

        // 取最早入队的命令执行
        auto cmd = std::move(buffer_.front());
        buffer_.pop();

        // 保存到历史（用于回放）
        history_.push_back(cmd->describe());
        cmd->execute();
    }

    bool hasInput() const { return !buffer_.empty(); }

    void showHistory() const {
        std::cout << "\n📼 回放记录:" << std::endl;
        for (size_t i = 0; i < history_.size(); i++) {
            std::cout << "  Frame " << i + 1 << ": " << history_[i] << std::endl;
        }
    }

private:
    std::queue<std::unique_ptr<Command>> buffer_;
    std::vector<std::string> history_;
};

// ============================================================
// 演示
// ============================================================
int main() {
    std::cout << "=== 命令模式演示（格斗游戏输入缓冲）===" << std::endl << std::endl;

    Fighter ryu;
    InputHandler input;

    // 玩家快速按键（可能在同一帧内）
    std::cout << "[玩家输入序列: ↓↘→P, K, P]" << std::endl << std::endl;

    input.enqueue(std::make_unique<SpecialCommand>(ryu));  // ↓↘→P
    input.enqueue(std::make_unique<KickCommand>(ryu));      // K
    input.enqueue(std::make_unique<PunchCommand>(ryu));     // P

    // 分帧执行
    std::cout << "--- Frame 1 ---" << std::endl;
    input.processFrame();

    std::cout << "\n--- Frame 2 ---" << std::endl;
    input.processFrame();

    std::cout << "\n--- Frame 3 ---" << std::endl;
    input.processFrame();

    // 展示回放
    input.showHistory();

    std::cout << "\n✅ 命令模式演示完成" << std::endl;
    return 0;
}
