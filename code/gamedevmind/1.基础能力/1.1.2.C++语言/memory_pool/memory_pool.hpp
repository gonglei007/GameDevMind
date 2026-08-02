#pragma once

#include <cstddef>      // size_t
#include <cstdint>      // uint32_t
#include <cassert>      // assert
#include <new>          // placement new
#include <utility>      // forward

// ===================================================================
// 游戏服务器内存池 (Memory Pool)
// 场景：假设管理 1000 个 NPC 对象，避免频繁 malloc/free 造成的
//       内存碎片和系统调用开销。
//
// 设计要点：
//   1. 固定大小块（所有块等大，适合同类型对象）
//   2. 自由链表（Free List）：空闲块通过内部指针串联，O(1) 分配/释放
//   3. DEBUG 模式：哨兵值检测越界写入 + 已释放标记检测 double-free
//   4. placement new / 显式析构，不依赖对象默认构造
// ===================================================================

namespace gdm {  // GameDevMind

// -------------------------------------------------------------------
// 编译期常量
// -------------------------------------------------------------------
constexpr uint32_t kPoolCanaryFront  = 0xDEADC0DE;  // 块前哨兵
constexpr uint32_t kPoolCanaryRear   = 0xC0DEDEAD;  // 块后哨兵
constexpr uint32_t kPoolFreedPattern = 0xFREEDBAA;  // 已释放标记（填充前4字节）

// -------------------------------------------------------------------
// MemoryPool<T, kBlockCount>
// -------------------------------------------------------------------
template <typename T, size_t kBlockCount>
class MemoryPool {
    static_assert(kBlockCount > 0, "Block count must be > 0");
    static_assert(sizeof(T) >= sizeof(void*),
                  "T must be at least pointer-sized for free-list embedding");

public:
    using value_type = T;
    static constexpr size_t kBlockSize   = sizeof(T);
    static constexpr size_t kPoolCapacity = kBlockCount;

    // ---------- 构造 / 析构 ----------

    MemoryPool() { init_free_list(); }

    ~MemoryPool() {
        // 注意：析构时不自动调用池中对象的析构函数。
        // 调用者应在销毁池之前确保所有对象已通过 Deallocate 归还。
    }

    // 禁止拷贝/移动（池拥有原始内存）
    MemoryPool(const MemoryPool&)            = delete;
    MemoryPool& operator=(const MemoryPool&) = delete;
    MemoryPool(MemoryPool&&)                 = delete;
    MemoryPool& operator=(MemoryPool&&)      = delete;

    // ---------- 核心接口 ----------

    /// 从池中分配一块内存，返回 T*（未初始化，建议配合 placement new）
    T* Allocate() {
        if (free_list_head_ == nullptr) {
            // 池已耗尽——生产环境应优雅降级，这里直接断言
            assert(false && "MemoryPool exhausted! Consider increasing kBlockCount.");
            return nullptr;
        }

        // 从自由链表摘取头部节点
        void* block = free_list_head_;
        free_list_head_ = *static_cast<void**>(block);  // 读取下一空闲块指针

#ifdef DEBUG
        // ---- DEBUG: 记录分配，用于 double-free 检测 ----
        auto* meta = get_meta(static_cast<T*>(block));
        assert(!meta->allocated && "Allocate: block already allocated (double-allocate bug?)");
        meta->allocated = true;

        // 校验前哨兵是否被越界破坏
        assert(meta->front_canary == kPoolCanaryFront &&
               "Allocate: front canary corrupted (buffer underflow detected!)");
        // 重置后哨兵（Deallocate 时已写入废模式，分配时恢复）
        meta->rear_canary = kPoolCanaryRear;
#endif

        return static_cast<T*>(block);
    }

    /// 归还一块内存到池中（需确保 ptr 来自本池的 Allocate）
    void Deallocate(T* ptr) {
        if (ptr == nullptr) return;

#ifdef DEBUG
        auto* meta = get_meta(ptr);

        // ---- DEBUG: double-free 检测 ----
        assert(meta->allocated && "Deallocate: block not allocated (double-free or bad pointer)!");
        meta->allocated = false;

        // ---- DEBUG: 越界检测（检查后哨兵） ----
        assert(meta->rear_canary == kPoolCanaryRear &&
               "Deallocate: rear canary corrupted (buffer overflow detected!)");

        // 用已知废模式填充内存，便于调试 use-after-free
        std::memset(ptr, 0xCD, sizeof(T));
        // 恢复前哨兵（可能被 memset 破坏）
        meta->front_canary = kPoolCanaryFront;
#endif

        // 将块插回自由链表头部（O(1)）
        void* block = static_cast<void*>(ptr);
        *static_cast<void**>(block) = free_list_head_;
        free_list_head_ = block;
    }

    /// 快捷方法：从池中分配并调用构造函数
    template <typename... Args>
    T* New(Args&&... args) {
        T* ptr = Allocate();
        if (ptr) {
            ::new (static_cast<void*>(ptr)) T(std::forward<Args>(args)...);
        }
        return ptr;
    }

    /// 快捷方法：调用析构函数并归还
    void Delete(T* ptr) {
        if (ptr) {
            ptr->~T();
            Deallocate(ptr);
        }
    }

    /// 查询池容量
    static constexpr size_t Capacity() { return kBlockCount; }
    /// 查询当前空闲块数（仅 DEBUG 模式做计数，release 靠 free_list 本身）
    size_t Available() const {
#ifdef DEBUG
        size_t n = 0;
        for (const auto* m = metas_; m < metas_ + kBlockCount; ++m) {
            if (!m->allocated) ++n;
        }
        return n;
#else
        size_t n = 0;
        for (void* cur = free_list_head_; cur; cur = *static_cast<void**>(cur)) ++n;
        return n;
#endif
    }

private:
    // ---------- 每个块的元数据（仅 DEBUG 模式启用） ----------
#ifdef DEBUG
    struct BlockMeta {
        uint32_t front_canary;   // 块前哨兵
        bool     allocated;      // 是否已分配
        // padding 隐式对齐
        uint32_t rear_canary;    // 块后哨兵
    };
#endif

    // ---------- 原始内存布局 ----------
    // 内存布局（每块）：
    //   [BlockMeta (DEBUG only)] [ T data ] [rear_canary (DEBUG only)]
    //
    // 为简化实现，BlockMeta 放在独立数组中，哨兵紧贴数据区两侧。
#ifdef DEBUG
    static constexpr size_t kBlockRawSize = sizeof(T) + 2 * sizeof(uint32_t);
    // raw_blocks_ 布局: [front_canary(4B)] [T data] [rear_canary(4B)]
    alignas(alignof(T)) unsigned char raw_blocks_[kBlockCount * kBlockRawSize];

    BlockMeta metas_[kBlockCount];
#else
    // Release 模式：纯对象数组，零开销
    alignas(alignof(T)) unsigned char blocks_[kBlockCount * sizeof(T)];
#endif

    void* free_list_head_ = nullptr;  // 自由链表头指针

    // ---------- 辅助：根据数据指针反查元数据 ----------
#ifdef DEBUG
    BlockMeta* get_meta(T* ptr) {
        auto* raw = reinterpret_cast<unsigned char*>(ptr);
        // raw 指向数据区开头，向前偏移 4 字节即 front_canary，再减 BlockMeta 大小即 metas_ 条目
        // 更简单的方式：通过地址差计算索引
        size_t offset = raw - raw_blocks_;
        size_t index  = offset / kBlockRawSize;
        assert(index < kBlockCount && "Pointer does not belong to this pool!");
        return &metas_[index];
    }

    const BlockMeta* get_meta(const T* ptr) const {
        return const_cast<MemoryPool*>(this)->get_meta(const_cast<T*>(ptr));
    }
#endif

    // ---------- 初始化自由链表 ----------
    void init_free_list() {
#ifdef DEBUG
        // 初始化所有块的哨兵和元数据
        for (size_t i = 0; i < kBlockCount; ++i) {
            unsigned char* raw = raw_blocks_ + i * kBlockRawSize;

            // 前哨兵
            uint32_t* front = reinterpret_cast<uint32_t*>(raw);
            *front = kPoolCanaryFront;

            // 后哨兵（紧接数据区之后）
            uint32_t* rear = reinterpret_cast<uint32_t*>(raw + sizeof(uint32_t) + sizeof(T));
            *rear = kPoolCanaryRear;

            // 元数据
            metas_[i].front_canary = kPoolCanaryFront;
            metas_[i].rear_canary  = kPoolCanaryRear;
            metas_[i].allocated    = false;
        }
#endif

        // 串联自由链表：block[i] -> block[i+1] -> ... -> nullptr
#ifdef DEBUG
        void* prev = nullptr;
        for (size_t i = kBlockCount; i > 0; --i) {
            // 数据区指针 = raw + 4（跳过前哨兵）
            void* data = raw_blocks_ + (i - 1) * kBlockRawSize + sizeof(uint32_t);
            *static_cast<void**>(data) = prev;
            prev = data;
        }
        free_list_head_ = prev;
#else
        for (size_t i = 0; i < kBlockCount; ++i) {
            void* block = blocks_ + i * sizeof(T);
            *static_cast<void**>(block) = free_list_head_;
            free_list_head_ = block;
        }
#endif
    }
};

} // namespace gdm
