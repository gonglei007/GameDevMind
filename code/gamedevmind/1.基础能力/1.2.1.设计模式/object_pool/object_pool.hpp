#pragma once
// ============================================================
// object_pool.hpp — 泛型对象池（游戏子弹 / 粒子系统优化）
// ============================================================
// 设计意图：
//   游戏每帧可能生成数百颗子弹/粒子，频繁 new/delete 会导致：
//     - 内存碎片化
//     - CPU 耗时波动（malloc 锁竞争）
//   对象池预分配一批对象，用完回收而非销毁，大幅提升帧率稳定性。
//
// 特性：
//   - 预分配 initial_size 个对象
//   - 池耗尽时自动扩容（翻倍策略）
//   - Acquire() 获取空闲对象，Release() 归还
//   - 线程不安全（游戏主线程专用，避免锁开销）
// ============================================================

#include <cassert>
#include <functional>
#include <iostream>
#include <memory>
#include <vector>

// -----------------------------------------------------------
// ObjectPool<T> — 泛型对象池
// -----------------------------------------------------------
template <typename T>
class ObjectPool {
public:
    // -------------------------------------------------------
    // 构造函数：预分配指定数量的对象
    // @param initial_size  初始池大小（建议根据游戏峰值估算）
    // @param constructor   可选的自定义构造回调
    // -------------------------------------------------------
    explicit ObjectPool(size_t initial_size = 256,
                        std::function<void(T&)> constructor = nullptr)
        : initial_size_(initial_size)
        , constructor_(std::move(constructor))
    {
        Resize(initial_size_);
    }

    ~ObjectPool() {
        // unique_ptr 自动释放所有对象
    }

    // 禁止拷贝和移动（pool 通常全局/单例使用）
    ObjectPool(const ObjectPool&) = delete;
    ObjectPool& operator=(const ObjectPool&) = delete;

    // -------------------------------------------------------
    // Acquire：从池中获取一个空闲对象
    //   如果池耗尽，自动扩容（翻倍）
    // -------------------------------------------------------
    T& Acquire() {
        if (free_list_.empty()) {
            Expand(); // 自动扩容
        }
        size_t index = free_list_.back();
        free_list_.pop_back();
        ++active_count_;

        // 重置对象状态（通过虚函数 Reset 或默认构造）
        if constexpr (requires(T& t) { t.Reset(); }) {
            pool_[index]->Reset();
        }

        return *pool_[index];
    }

    // -------------------------------------------------------
    // Release：将对象归还池中供复用
    //   注意：调用者负责不再持有该对象的引用
    // -------------------------------------------------------
    void Release(T& obj) {
        // 通过地址查找索引（简单线性搜索，生产环境可用对象内嵌 index）
        for (size_t i = 0; i < pool_.size(); ++i) {
            if (pool_[i].get() == &obj) {
                free_list_.push_back(i);
                --active_count_;
                return;
            }
        }
        // 不应到达这里：归还了不属于本池的对象
        assert(false && "ObjectPool::Release: object does not belong to this pool!");
    }

    // -------------------------------------------------------
    // 统计信息
    // -------------------------------------------------------
    size_t TotalSize()   const { return pool_.size(); }
    size_t ActiveCount() const { return active_count_; }
    size_t FreeCount()   const { return free_list_.size(); }

    void PrintStats(const char* label = "ObjectPool") const {
        std::cout << "[" << label << "] 总容量=" << TotalSize()
                  << " 使用中=" << ActiveCount()
                  << " 空闲=" << FreeCount()
                  << " 扩容次数=" << expand_count_
                  << std::endl;
    }

private:
    // -------------------------------------------------------
    // Resize：扩容到指定大小
    // -------------------------------------------------------
    void Resize(size_t new_size) {
        size_t old_size = pool_.size();
        pool_.reserve(new_size);
        free_list_.reserve(new_size);

        for (size_t i = old_size; i < new_size; ++i) {
            pool_.push_back(std::make_unique<T>());
            if (constructor_) {
                constructor_(*pool_.back());
            }
            free_list_.push_back(i);
        }
    }

    // -------------------------------------------------------
    // Expand：自动扩容（翻倍）
    // -------------------------------------------------------
    void Expand() {
        size_t new_size = std::max(pool_.size() * 2, initial_size_);
        std::cout << "  [ObjectPool] ⚠️ 池耗尽，自动扩容: "
                  << pool_.size() << " → " << new_size << std::endl;
        Resize(new_size);
        ++expand_count_;
    }

    size_t initial_size_ = 256;
    size_t active_count_ = 0;
    size_t expand_count_ = 0;

    std::vector<std::unique_ptr<T>> pool_;    // 对象存储
    std::vector<size_t> free_list_;            // 空闲索引栈

    std::function<void(T&)> constructor_;      // 构造回调
};
