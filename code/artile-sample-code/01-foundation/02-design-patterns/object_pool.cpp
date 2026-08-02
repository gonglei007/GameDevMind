/**
 * 对象池模式 — 游戏开发中的子弹/粒子管理
 *
 * 对应文章：一-02-设计模式实战 / 一-05-内存管理深度解析
 *
 * 场景：弹幕游戏中每秒产生数百颗子弹，
 * 如果频繁 new/delete 会导致内存碎片和 GC 抖动。
 * 对象池预先分配并循环复用。
 */

#include <iostream>
#include <vector>
#include <queue>
#include <memory>

// ============================================================
// 可池化的对象
// ============================================================
class Bullet {
public:
    Bullet() : id_(++globalId_) {}

    void fire(float x, float y, float vx, float vy) {
        x_ = x; y_ = y; vx_ = vx; vy_ = vy;
        active_ = true;
    }

    void update(float dt) {
        if (!active_) return;
        x_ += vx_ * dt;
        y_ += vy_ * dt;
        lifetime_ -= dt;
        if (lifetime_ <= 0) active_ = false;
    }

    void reset() {
        x_ = y_ = vx_ = vy_ = 0;
        lifetime_ = 5.0f;
        active_ = false;
    }

    bool active() const { return active_; }
    int id() const { return id_; }
    float x() const { return x_; }
    float y() const { return y_; }

private:
    static inline int globalId_ = 0;
    int id_;
    float x_ = 0, y_ = 0, vx_ = 0, vy_ = 0;
    float lifetime_ = 5.0f;
    bool active_ = false;
};

// ============================================================
// 对象池
// ============================================================
template<typename T>
class ObjectPool {
public:
    explicit ObjectPool(size_t initialSize = 32) {
        for (size_t i = 0; i < initialSize; i++) {
            auto obj = std::make_unique<T>();
            obj->reset();
            available_.push(obj.get());
            allObjects_.push_back(std::move(obj));
        }
    }

    T* acquire() {
        if (available_.empty()) {
            // 池耗尽：动态扩展
            std::cout << "  ⚠️  对象池扩展 (+16)" << std::endl;
            for (int i = 0; i < 16; i++) {
                auto obj = std::make_unique<T>();
                obj->reset();
                available_.push(obj.get());
                allObjects_.push_back(std::move(obj));
            }
        }
        T* obj = available_.front();
        available_.pop();
        return obj;
    }

    void release(T* obj) {
        obj->reset();
        available_.push(obj);
    }

    size_t available() const { return available_.size(); }
    size_t total() const { return allObjects_.size(); }

private:
    std::queue<T*> available_;
    std::vector<std::unique_ptr<T>> allObjects_;
};

// ============================================================
// 演示
// ============================================================
int main() {
    std::cout << "=== 对象池演示（子弹管理）===" << std::endl << std::endl;

    ObjectPool<Bullet> pool(4);  // 初始 4 颗子弹
    std::cout << "池初始大小: " << pool.total()
              << "，可用: " << pool.available() << std::endl;

    // 发射 6 颗子弹（触发扩展）
    std::vector<Bullet*> active;
    std::cout << "\n[发射 6 颗子弹]" << std::endl;
    for (int i = 0; i < 6; i++) {
        auto* b = pool.acquire();
        b->fire(i * 10.0f, 0, 1.0f, 0.5f);
        active.push_back(b);
        std::cout << "  Bullet #" << b->id() << " fired at (" << b->x() << ", 0)" << std::endl;
    }
    std::cout << "池状态: 共 " << pool.total() << "，可用 " << pool.available() << std::endl;

    // 回收 4 颗
    std::cout << "\n[回收 4 颗子弹]" << std::endl;
    for (int i = 0; i < 4; i++) {
        std::cout << "  回收 Bullet #" << active[i]->id() << std::endl;
        pool.release(active[i]);
    }
    std::cout << "池状态: 共 " << pool.total() << "，可用 " << pool.available() << std::endl;

    // 再次获取（复用回收的）
    std::cout << "\n[再次获取 2 颗]" << std::endl;
    auto* b1 = pool.acquire();
    auto* b2 = pool.acquire();
    std::cout << "  复用 Bullet #" << b1->id() << " 和 #" << b2->id() << std::endl;

    std::cout << "\n✅ 对象池演示完成" << std::endl;
    return 0;
}
