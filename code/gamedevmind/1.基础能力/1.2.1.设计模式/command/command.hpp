#pragma once
// ============================================================
// command.hpp — 命令模式：游戏输入命令体系
// ============================================================
// 设计意图：
//   将玩家输入（移动、攻击、技能）封装为独立命令对象，
//   方便录制、撤销、回放。这是 RTS/格斗游戏回放系统的基础。
// ============================================================

#include <functional>
#include <iostream>
#include <memory>
#include <string>

// -----------------------------------------------------------
// 玩家状态（命令执行的目标上下文）
// -----------------------------------------------------------
struct Player {
    std::string name;
    int pos_x = 0;   // 玩家 X 坐标
    int pos_y = 0;   // 玩家 Y 坐标
    int hp    = 100; // 生命值

    void Print() const {
        std::cout << "  Player[" << name << "] pos=(" << pos_x << "," << pos_y
                  << ") hp=" << hp << std::endl;
    }
};

// -----------------------------------------------------------
// ICommand — 命令基类（抽象接口）
// -----------------------------------------------------------
class ICommand {
public:
    virtual ~ICommand() = default;

    // 执行命令
    virtual void Execute(Player& player) = 0;

    // 撤销命令（恢复执行前的状态）
    virtual void Undo(Player& player) = 0;

    // 用于调试/回放展示
    virtual std::string GetName() const = 0;
};

// -----------------------------------------------------------
// MoveCommand — 移动命令
// -----------------------------------------------------------
class MoveCommand : public ICommand {
public:
    MoveCommand(int dx, int dy) : delta_x_(dx), delta_y_(dy) {}

    void Execute(Player& player) override {
        // 保存旧位置以便撤销
        old_x_ = player.pos_x;
        old_y_ = player.pos_y;
        player.pos_x += delta_x_;
        player.pos_y += delta_y_;
    }

    void Undo(Player& player) override {
        player.pos_x = old_x_;
        player.pos_y = old_y_;
    }

    std::string GetName() const override {
        return "Move(" + std::to_string(delta_x_) + "," + std::to_string(delta_y_) + ")";
    }

private:
    int delta_x_, delta_y_; // 移动增量
    int old_x_ = 0, old_y_ = 0; // 用于撤销
};

// -----------------------------------------------------------
// AttackCommand — 攻击命令
// -----------------------------------------------------------
class AttackCommand : public ICommand {
public:
    explicit AttackCommand(int damage) : damage_(damage) {}

    void Execute(Player& player) override {
        // 保存旧 HP（虽然攻击不消耗自己 HP，这里模拟"攻击动作"的状态变化）
        old_hp_ = player.hp;
        // 游戏场景：攻击消耗少量精力，体现为 HP 略微变化
        // （实际游戏中攻击会改变目标 HP，这里为演示简化）
    }

    void Undo(Player& player) override {
        player.hp = old_hp_;
    }

    std::string GetName() const override {
        return "Attack(dmg=" + std::to_string(damage_) + ")";
    }

private:
    int damage_;
    int old_hp_ = 0;
};

// -----------------------------------------------------------
// SkillCommand — 技能命令（带执行回调，更灵活）
// -----------------------------------------------------------
class SkillCommand : public ICommand {
public:
    using SkillFunc = std::function<void(Player&)>;

    SkillCommand(std::string skill_name, SkillFunc execute_fn, SkillFunc undo_fn)
        : name_(std::move(skill_name))
        , execute_fn_(std::move(execute_fn))
        , undo_fn_(std::move(undo_fn)) {}

    void Execute(Player& player) override {
        // 保存完整状态快照
        snapshot_ = player;
        execute_fn_(player);
    }

    void Undo(Player& player) override {
        undo_fn_(player);
        // 或者直接恢复快照：
        // player = snapshot_;
    }

    std::string GetName() const override { return "Skill:" + name_; }

private:
    std::string name_;
    SkillFunc execute_fn_;
    SkillFunc undo_fn_;
    Player snapshot_; // 状态快照，用于最安全的撤销
};
