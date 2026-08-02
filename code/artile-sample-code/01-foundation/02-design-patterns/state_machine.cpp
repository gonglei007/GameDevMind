/**
 * 游戏角色状态机 — State 模式
 *
 * 对应文章：一-02-设计模式实战
 * 每个角色都有 Idle / Run / Attack / Dead 等状态，
 * 用状态模式替代 if-else 嵌套，清晰可扩展。
 */

#include <iostream>
#include <string>
#include <memory>

// ============================================================
// 前向声明
// ============================================================
class Character;

// ============================================================
// 状态基类
// ============================================================
class CharacterState {
public:
    virtual ~CharacterState() = default;
    virtual void enter(Character&) {}
    virtual void update(Character&) {}
    virtual void exit(Character&) {}
    virtual std::string name() const = 0;
};

// ============================================================
// 角色类
// ============================================================
class Character {
public:
    Character(const std::string& name, int hp)
        : name_(name), hp_(hp), maxHp_(hp) {}

    void changeState(std::unique_ptr<CharacterState> newState) {
        if (state_) state_->exit(*this);
        state_ = std::move(newState);
        if (state_) state_->enter(*this);
    }

    void update() {
        if (state_) state_->update(*this);
    }

    void takeDamage(int dmg) {
        hp_ -= dmg;
        std::cout << "  " << name_ << " 受到 " << dmg << " 点伤害 (HP: " << hp_ << ")" << std::endl;
    }

    const std::string& name() const { return name_; }
    int hp() const { return hp_; }
    int maxHp() const { return maxHp_; }
    std::string stateName() const { return state_ ? state_->name() : "None"; }

private:
    std::string name_;
    int hp_, maxHp_;
    std::unique_ptr<CharacterState> state_;
};

// ============================================================
// 具体状态
// ============================================================

class IdleState : public CharacterState {
public:
    std::string name() const override { return "Idle"; }
    void enter(Character& c) override {
        std::cout << "🧍 " << c.name() << " 进入待机状态" << std::endl;
    }
    void update(Character& c) override {
        // 播放待机动画、随机小动作
    }
};

class RunState : public CharacterState {
public:
    std::string name() const override { return "Run"; }
    void enter(Character& c) override {
        std::cout << "🏃 " << c.name() << " 开始奔跑" << std::endl;
    }
};

class AttackState : public CharacterState {
public:
    std::string name() const override { return "Attack"; }
    void enter(Character& c) override {
        std::cout << "⚔️  " << c.name() << " 开始攻击" << std::endl;
        comboCount_ = 0;
    }
    void update(Character&) override {
        if (++comboCount_ >= 3) {
            std::cout << "  ✨ 三连击！" << std::endl;
        }
    }
private:
    int comboCount_ = 0;
};

class DeadState : public CharacterState {
public:
    std::string name() const override { return "Dead"; }
    void enter(Character& c) override {
        std::cout << "💀 " << c.name() << " 已阵亡" << std::endl;
    }
};

// ============================================================
// 演示
// ============================================================
int main() {
    std::cout << "=== 游戏角色状态机演示 ===" << std::endl << std::endl;

    Character hero("英雄", 100);
    hero.changeState(std::make_unique<IdleState>());

    std::cout << "\n[玩家操作：移动]" << std::endl;
    hero.changeState(std::make_unique<RunState>());
    std::cout << "  当前状态: " << hero.stateName() << std::endl;

    std::cout << "\n[玩家操作：攻击]" << std::endl;
    hero.changeState(std::make_unique<AttackState>());
    for (int i = 0; i < 4; i++) hero.update();

    std::cout << "\n[受到致命伤害]" << std::endl;
    hero.takeDamage(120);
    if (hero.hp() <= 0) {
        hero.changeState(std::make_unique<DeadState>());
    }
    std::cout << "  当前状态: " << hero.stateName() << std::endl;

    std::cout << "\n✅ 状态机演示完成" << std::endl;
    return 0;
}
