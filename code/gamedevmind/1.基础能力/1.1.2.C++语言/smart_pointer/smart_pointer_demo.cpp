/**
 * smart_pointer_demo.cpp
 * C++ 智能指针陷阱与最佳实践 — 5 大场景演示
 * 
 * 编译: g++ -std=c++17 -O2 -Wall smart_pointer_demo.cpp -o smart_pointer_demo
 * 运行: ./smart_pointer_demo
 *
 * 对应图谱: mds/1.基础能力/1.1.2.C++语言.md → 智能指针章节
 */

#include <iostream>
#include <memory>
#include <vector>
#include <string>
#include <cassert>

// ============================================================
// 通用工具：析构计数与日志
// ============================================================
static int g_live_objects = 0;  // 全局存活对象计数
inline void log_dtor(const char* name) {
    --g_live_objects;
    std::cout << "  [析构] " << name << " (存活: " << g_live_objects << ")" << std::endl;
}
inline void log_ctor(const char* name) {
    ++g_live_objects;
    std::cout << "  [构造] " << name << " (存活: " << g_live_objects << ")" << std::endl;
}
inline void print_separator(const char* title) {
    std::cout << "\n========== " << title << " ==========" << std::endl;
}
#define RESET_COUNT() (g_live_objects = 0)

// ============================================================
// 场景 A: unique_ptr 正确用法 — 工厂函数 + 容器存储
// ============================================================
namespace scene_a {

struct GameObject {
    std::string name;
    explicit GameObject(std::string n) : name(std::move(n)) {
        log_ctor(name.c_str());
    }
    ~GameObject() { log_dtor(name.c_str()); }
    void update() { std::cout << "    " << name << "::update()" << std::endl; }
};

// 工厂函数：返回 unique_ptr，所有权明确转移给调用者
std::unique_ptr<GameObject> create_game_object(const std::string& name) {
    return std::make_unique<GameObject>(name);
}

void demo() {
    print_separator("场景A: unique_ptr 工厂函数 + 容器存储");

    // 容器存储 unique_ptr（不可复制，只能移动）
    std::vector<std::unique_ptr<GameObject>> objects;
    objects.push_back(create_game_object("Player"));
    objects.push_back(create_game_object("Enemy"));
    objects.push_back(create_game_object("Boss"));

    // 遍历
    for (auto& obj : objects) {
        obj->update();
    }

    // 转移所有权
    auto boss = std::move(objects.back());
    objects.pop_back();
    std::cout << "  Boss 所有权已转移出容器" << std::endl;

    // 离开作用域，所有 unique_ptr 自动释放
    std::cout << "  --- 离开作用域，自动析构 ---" << std::endl;
}

} // namespace scene_a

// ============================================================
// 场景 B: shared_ptr 循环引用 → 内存泄漏
// ============================================================
namespace scene_b {

struct Child;  // 前向声明

struct Parent {
    std::string name;
    std::shared_ptr<Child> child_ptr;
    explicit Parent(std::string n) : name(std::move(n)) { log_ctor(name.c_str()); }
    ~Parent() { log_dtor(name.c_str()); }
};

struct Child {
    std::string name;
    std::shared_ptr<Parent> parent_ptr;  // ★ 循环引用！
    explicit Child(std::string n) : name(std::move(n)) { log_ctor(name.c_str()); }
    ~Child() { log_dtor(name.c_str()); }
};

// 泄漏场景：Parent ↔ Child 互相持有 shared_ptr
void demo_leak() {
    print_separator("场景B: shared_ptr 循环引用 → 泄漏");

    auto parent = std::make_shared<Parent>("Parent_Leak");
    auto child  = std::make_shared<Child>("Child_Leak");

    parent->child_ptr  = child;    // Parent 持有 Child
    child->parent_ptr  = parent;   // Child 持有 Parent → 循环！

    std::cout << "  parent.use_count() = " << parent.use_count() << std::endl;  // 2
    std::cout << "  child.use_count()  = " << child.use_count()  << std::endl;  // 2

    // parent 和 child 离开作用域 → use_count 从 2 降为 1，永不归零！
    std::cout << "  --- 离开作用域 (预期：析构函数不会被调用！) ---" << std::endl;
}

void demo() {
    int before = g_live_objects;
    {
        demo_leak();
    }
    int after = g_live_objects;
    std::cout << "\n  ⚠ 泄漏检测: 离开作用域后仍有 " << (after - before)
              << " 个对象未被析构！(应为 0)" << std::endl;
    if (after > before) {
        std::cout << "  ⚠ 这就是 shared_ptr 循环引用导致的内存泄漏！" << std::endl;
    }
}

} // namespace scene_b

// ============================================================
// 场景 C: weak_ptr 打破循环引用 → 修复
// ============================================================
namespace scene_c {

struct Parent;

struct Child {
    std::string name;
    std::weak_ptr<Parent> parent_weak;  // ★ weak_ptr 打破循环！
    explicit Child(std::string n) : name(std::move(n)) { log_ctor(name.c_str()); }
    ~Child() { log_dtor(name.c_str()); }

    // 安全访问父对象（需要 lock）
    void talk_to_parent() {
        if (auto p = parent_weak.lock()) {
            std::cout << "    " << name << " 在和 " << p->name << " 说话" << std::endl;
        } else {
            std::cout << "    " << name << ": 父对象已不存在" << std::endl;
        }
    }
};

struct Parent {
    std::string name;
    std::shared_ptr<Child> child_ptr;   // 这一侧仍然用 shared_ptr
    explicit Parent(std::string n) : name(std::move(n)) { log_ctor(name.c_str()); }
    ~Parent() { log_dtor(name.c_str()); }
};

void demo_fixed() {
    print_separator("场景C: weak_ptr 打破循环引用 → 修复");

    auto parent = std::make_shared<Parent>("Parent_Fixed");
    auto child  = std::make_shared<Child>("Child_Fixed");

    parent->child_ptr   = child;          // Parent 持有 Child (shared)
    child->parent_weak  = parent;         // Child 持有 Parent (weak) → 不增加计数！

    std::cout << "  parent.use_count() = " << parent.use_count() << std::endl;  // 1 ✓
    std::cout << "  child.use_count()  = " << child.use_count()  << std::endl;  // 2 (parent->child_ptr + child)

    child->talk_to_parent();

    // 离开作用域 → parent 先析构，child 的 use_count 降为 1 然后析构
    std::cout << "  --- 离开作用域 (预期：析构函数会被正确调用) ---" << std::endl;
}

void demo() {
    int before = g_live_objects;
    {
        demo_fixed();
    }
    int after = g_live_objects;
    std::cout << "\n  ✅ 修复验证: 离开作用域后存活对象: " << (after - before)
              << " (应为 0)" << std::endl;
    if (after == before) {
        std::cout << "  ✅ weak_ptr 成功打破了循环引用！" << std::endl;
    }
}

} // namespace scene_c

// ============================================================
// 场景 D: 返回裸指针 / 引用 / 智能指针的选择指南
// ============================================================
namespace scene_d {

struct Texture {
    int id;
    explicit Texture(int i) : id(i) { std::cout << "    Texture(" << id << ") 创建" << std::endl; }
    ~Texture() { std::cout << "    Texture(" << id << ") 销毁" << std::endl; }
    void draw() const { std::cout << "    Texture(" << id << ")::draw()" << std::endl; }
};

struct TextureManager {
    std::vector<std::unique_ptr<Texture>> textures;

    void load(int id) {
        textures.push_back(std::make_unique<Texture>(id));
    }

    // 规则1: 返回裸指针 — 用于"非拥有型"访问，调用者不负责释放
    // 前提：指针指向的对象生命周期 > 调用者使用周期
    Texture* get_raw(int id) {
        for (auto& t : textures) {
            if (t->id == id) return t.get();
        }
        return nullptr;
    }

    // 规则2: 返回引用 — 当对象一定存在时，比裸指针更安全（不可为空）
    Texture& get_ref(int id) {
        Texture* p = get_raw(id);
        assert(p != nullptr && "Texture not found!");
        return *p;
    }

    // 规则3: 返回 unique_ptr — 所有权转移给调用者
    std::unique_ptr<Texture> release(int id) {
        for (auto it = textures.begin(); it != textures.end(); ++it) {
            if ((*it)->id == id) {
                auto result = std::move(*it);
                textures.erase(it);
                return result;
            }
        }
        return nullptr;
    }

    // 规则4: 返回 shared_ptr — 共享所有权（内部存储应为 shared_ptr）
    // 此处仅演示签名，实际需将 storage 改为 vector<shared_ptr<Texture>>
};

void demo() {
    print_separator("场景D: 返回值类型选择指南");

    std::cout << "\n  --- 指南 ---" << std::endl;
    std::cout << "  | 返回值类型     | 何时使用                                     |" << std::endl;
    std::cout << "  |----------------|---------------------------------------------|" << std::endl;
    std::cout << "  | 裸指针 T*      | 非拥有型访问；可能为空；生命周期由调用者保证 |" << std::endl;
    std::cout << "  | 引用 T&        | 非拥有型访问；一定存在；不可为空语义         |" << std::endl;
    std::cout << "  | unique_ptr<T>  | 所有权转移给调用者；独占语义                 |" << std::endl;
    std::cout << "  | shared_ptr<T>  | 共享所有权；多个调用者共同持有               |" << std::endl;
    std::cout << "  | weak_ptr<T>    | 观察共享对象；不控制生命周期                 |" << std::endl;

    TextureManager mgr;
    mgr.load(100);
    mgr.load(200);

    std::cout << "\n  --- 示例: 裸指针访问 ---" << std::endl;
    // 裸指针：不拥有所有权
    Texture* raw = mgr.get_raw(100);
    if (raw) raw->draw();

    std::cout << "\n  --- 示例: 引用访问 ---" << std::endl;
    // 引用：保证非空
    Texture& ref = mgr.get_ref(200);
    ref.draw();

    std::cout << "\n  --- 示例: 所有权转移 ---" << std::endl;
    // unique_ptr：所有权转移
    auto released = mgr.release(100);
    released->draw();
    // released 离开作用域时 Texture(100) 被销毁
    std::cout << "    released 离开作用域 → Texture(100) 将被销毁" << std::endl;

    std::cout << "\n  --- 容器中剩余对象 ---" << std::endl;
    mgr.get_ref(200).draw();
}

} // namespace scene_d

// ============================================================
// 场景 E: make_unique / make_shared 优于 new 的原因
// ============================================================
namespace scene_e {

struct Resource {
    int id;
    explicit Resource(int i) : id(i) {
        std::cout << "    Resource(" << id << ") 分配" << std::endl;
    }
    ~Resource() {
        std::cout << "    Resource(" << id << ") 释放" << std::endl;
    }
};

struct RiskClass {
    Resource r1;
    Resource r2;
    RiskClass(int a, int b) : r1(a), r2(b) {
        // 假设这里可能抛出异常
        if (a == 0 || b == 0) throw std::runtime_error("构造失败");
    }
};

void demo() {
    print_separator("场景E: make_unique / make_shared 优于 new");

    // -------------------------------------------------------
    // 原因1: 单次内存分配 (make_shared)
    // -------------------------------------------------------
    std::cout << "\n  --- 原因1: make_shared 单次内存分配 ---" << std::endl;
    std::cout << "  new shared_ptr<T>(new T):  2次分配 (控制块 + 对象)" << std::endl;
    std::cout << "  make_shared<T>():           1次分配 (控制块+对象合并)" << std::endl;
    std::cout << "  → 更少内存碎片，更好的缓存局部性" << std::endl;

    // -------------------------------------------------------
    // 原因2: 异常安全
    // -------------------------------------------------------
    std::cout << "\n  --- 原因2: 异常安全 ---" << std::endl;

#if 0
    // ★ 错误写法：new 可能泄漏
    // 如果第二个 new 抛出异常，第一个 new 的对象会泄漏！
    void risky_function() {
        // 编译器可能按以下顺序求值：
        //   1) new RiskClass(1, 2)    → 分配对象A
        //   2) new RiskClass(3, 0)    → 抛出异常！
        //   3) shared_ptr 构造函数  → 永远不会执行
        // 结果：对象A 泄漏！
        std::shared_ptr<RiskClass> sp1(new RiskClass(1, 2));
        std::shared_ptr<RiskClass> sp2(new RiskClass(3, 0));  // 可能泄漏
    }
#endif

    // ★ 正确写法：make_shared 保证异常安全
    std::cout << "  测试: make_shared 的异常安全性" << std::endl;
    try {
        auto sp1 = std::make_shared<RiskClass>(1, 2);
        auto sp2 = std::make_shared<RiskClass>(3, 0);  // 抛异常，但 sp1 安全
    } catch (const std::exception& e) {
        std::cout << "    捕获异常: " << e.what() << std::endl;
        std::cout << "    sp1 的 Resource(1) 和 Resource(2) 正确释放 ✓" << std::endl;
    }

    // -------------------------------------------------------
    // 原因3: 代码简洁，类型不重复
    // -------------------------------------------------------
    std::cout << "\n  --- 原因3: 代码简洁 ---" << std::endl;

#if 0
    std::unique_ptr<Resource> p1(new Resource(1));                  // 重复写 Resource
    std::shared_ptr<Resource> p2(new Resource(2));                  // 重复写 Resource
#endif

    auto p3 = std::make_unique<Resource>(42);  // 简洁，类型推导
    auto p4 = std::make_shared<Resource>(43);  // 简洁，类型推导
    std::cout << "    make_unique<Resource>(42) — 类型只写一次" << std::endl;
    std::cout << "    make_shared<Resource>(43)  — 类型只写一次" << std::endl;

    // -------------------------------------------------------
    // 原因4: 代码审查更容易发现 new
    // -------------------------------------------------------
    std::cout << "\n  --- 原因4: 代码审查 ---" << std::endl;
    std::cout << "    如果代码中出现 'new'，应审视是否应该用 make_unique/make_shared" << std::endl;
    std::cout << "    new 只在以下情况合理:" << std::endl;
    std::cout << "      - make_shared 不适合（自定义删除器、weak_ptr 延长控制块生命等）" << std::endl;
    std::cout << "      - placement new" << std::endl;
    std::cout << "      - 使用已有裸指针构造 shared_ptr（如 C API 返回的指针）" << std::endl;

    std::cout << "\n  ✅ make_unique / make_shared 应是默认选择！" << std::endl;
}

} // namespace scene_e

// ============================================================
// 主函数
// ============================================================
int main() {
    std::cout << "╔══════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║   C++ 智能指针陷阱与最佳实践 — 5 大场景演示            ║" << std::endl;
    std::cout << "║   对应: 1.1.2 C++语言 → 智能指针章节                  ║" << std::endl;
    std::cout << "╚══════════════════════════════════════════════════════════╝" << std::endl;

    // ---- 场景 A ----
    RESET_COUNT();
    scene_a::demo();

    // ---- 场景 B: 泄漏 ----
    RESET_COUNT();
    scene_b::demo();

    // ---- 场景 C: 修复 ----
    RESET_COUNT();
    scene_c::demo();

    // ---- 场景 D ----
    scene_d::demo();

    // ---- 场景 E ----
    scene_e::demo();

    std::cout << "\n============================================" << std::endl;
    std::cout << "所有场景演示完毕。" << std::endl;
    return 0;
}
