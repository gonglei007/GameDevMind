# C++ 智能指针陷阱与最佳实践

> 对应图谱章节：[1.1.2 C++语言 → 智能指针](../../../../mds/1.基础能力/1.1.2.C++语言.md#智能指针)

## 快速开始

```bash
# 直接编译运行
g++ -std=c++17 -O2 -Wall smart_pointer_demo.cpp -o smart_pointer_demo && ./smart_pointer_demo

# 或通过 CMake
mkdir build && cd build && cmake .. && make && ./smart_pointer_demo
```

## 五大陷阱与最佳实践总结

| # | 陷阱 / 场景 | 问题描述 | 解决方案 | 代码位置 |
|---|------------|---------|---------|---------|
| 1 | **unique_ptr 误用** | 尝试复制 unique_ptr；忘记移动语义；手动 new/delete 管理裸指针 | 工厂函数返回 unique_ptr；容器存储用 `std::move`；`make_unique` 构造 | 场景A |
| 2 | **shared_ptr 循环引用** | 两个对象互相持有 `shared_ptr`，引用计数永不归零 → 内存泄漏 | 将其中一侧改为 `weak_ptr`；重新审视所有权设计 | 场景B/C |
| 3 | **返回类型选择不当** | 返回裸指针导致所有权混乱；返回引用导致悬空引用 | 非拥有 → 裸指针/引用；转移所有权 → `unique_ptr`；共享 → `shared_ptr` | 场景D |
| 4 | **weak_ptr 不检查就使用** | 直接解引用 `weak_ptr`；`lock()` 返回空未处理 | 每次使用前 `lock()` 并检查返回值；利用 `expired()` 判断 | 场景C |
| 5 | **使用 new 而非 make_*** | 异常不安全；双重内存分配（shared_ptr）；代码冗余 | 默认用 `make_unique` / `make_shared`；仅在自定义删除器等场景用 new | 场景E |

---

## 场景详解

### 场景 A：unique_ptr 正确用法

**陷阱**：误用 `unique_ptr` — 尝试复制、忘记移动语义、手动 `new`/`delete`。

**演示内容**：
- 工厂函数 `create_game_object()` 返回 `unique_ptr<GameObject>`，所有权唯一且明确
- `std::vector<std::unique_ptr<GameObject>>` 存储不可复制对象
- `std::move` 转移所有权
- 离开作用域自动析构，无需手动 `delete`

**对应图谱**：智能指针 → 类型 → unique_ptr（独占，不能复制只能移动）

---

### 场景 B：shared_ptr 循环引用 → 泄漏 ⚠

**陷阱**：`Parent` 持有 `shared_ptr<Child>`，`Child` 持有 `shared_ptr<Parent>`，形成循环。

**泄漏机制**：
```
创建后:
  parent.use_count() = 2   (parent 变量 + child->parent_ptr)
  child.use_count()  = 2   (child 变量  + parent->child_ptr)

离开作用域后:
  parent.use_count() = 1   (仅 child->parent_ptr 持有)
  child.use_count()  = 1   (仅 parent->child_ptr 持有)
  → 引用计数永不归零 → 两个对象的析构函数永不调用 → 内存泄漏！
```

**运行输出示例**（重点观察析构日志）：
```
========== 场景B: shared_ptr 循环引用 → 泄漏 ==========
  [构造] Parent_Leak (存活: 1)
  [构造] Child_Leak (存活: 2)
  parent.use_count() = 2
  child.use_count() = 2
  --- 离开作用域 (预期：析构函数不会被调用！) ---
  ⚠ 泄漏检测: 离开作用域后仍有 2 个对象未被析构！(应为 0)
  ⚠ 这就是 shared_ptr 循环引用导致的内存泄漏！
```

> 🔑 **关键对比点**：注意场景B离开作用域后 **没有** 出现 `[析构]` 日志！

**对应图谱**：智能指针 → 问题 → 循环引用

---

### 场景 C：weak_ptr 打破循环引用 → 修复 ✅

**解决方案**：`Child` 改用 `weak_ptr<Parent>`，不增加引用计数。

**修复机制**：
```
创建后:
  parent.use_count() = 1   (仅 parent 变量持有)
  child.use_count()  = 2   (child 变量 + parent->child_ptr)
  → weak_ptr 不计入引用计数！

离开作用域后:
  parent 离开 → use_count 0 → Parent 析构
  parent->child_ptr 释放 → child.use_count 从2降为1
  child 离开 → use_count 0 → Child 析构
  → 全部正常释放！
```

**运行输出示例**（与B对比）：
```
========== 场景C: weak_ptr 打破循环引用 → 修复 ==========
  [构造] Parent_Fixed (存活: 1)
  [构造] Child_Fixed (存活: 2)
  parent.use_count() = 1
  child.use_count() = 2
  Child_Fixed 在和 Parent_Fixed 说话
  --- 离开作用域 (预期：析构函数会被正确调用) ---
  [析构] Parent_Fixed (存活: 1)
  [析构] Child_Fixed (存活: 0)
  ✅ 修复验证: 离开作用域后存活对象: 0 (应为 0)
  ✅ weak_ptr 成功打破了循环引用！
```

> 🔑 **修复后的析构日志清晰可见**：`Parent_Fixed` 和 `Child_Fixed` 依次析构，存活对象归零。

**对应图谱**：智能指针 → 问题 → 循环引用：使用 weak_ptr 打破

---

### 场景 D：返回值类型选择指南

| 返回值类型 | 语义 | 适用场景 |
|-----------|------|---------|
| `T*`（裸指针） | 非拥有型访问，可空 | 访问容器内元素；可选参数；C API 交互 |
| `T&`（引用） | 非拥有型访问，不可空 | 对象一定存在时；运算符重载 |
| `unique_ptr<T>` | 所有权转移 | 工厂函数；释放独占资源给调用者 |
| `shared_ptr<T>` | 共享所有权 | 多线程共享；缓存；观察者模式 |
| `weak_ptr<T>` | 观察共享对象 | 打破循环引用；缓存失效检测 |

**对应图谱**：智能指针 → 类型；智能指针 → 问题 → 原始指针混用

---

### 场景 E：make_unique / make_shared 优于 new

| 维度 | `new` 方式 | `make_*` 方式 |
|------|-----------|--------------|
| 内存分配 | `shared_ptr<T>(new T)` 分配2次 | `make_shared<T>()` 分配1次 |
| 异常安全 | `f(shared_ptr<T>(new T), g())` 可能泄漏 | `make_shared` 保证安全 |
| 代码简洁 | `shared_ptr<Foo> p(new Foo(1,2,3))` | `auto p = make_shared<Foo>(1,2,3)` |
| 代码审查 | 出现 `new` 需审视 | 默认最佳实践 |

**exception safety 详解**（`#if 0` 包裹的错误代码）：
```cpp
// 潜在泄漏：如果第二个 new 抛异常，第一个 new 的对象泄漏
f(shared_ptr<T>(new T), shared_ptr<T>(new T));

// 安全：make_shared 保证要么全部成功，要么全部回滚
f(make_shared<T>(), make_shared<T>());
```

**对应图谱**：智能指针 → 内部实现

---

## 核心要点

1. **默认使用智能指针**，避免裸 `new`/`delete`
2. **unique_ptr 是首选**：零开销，独占所有权
3. **需要共享时才用 shared_ptr**：有引用计数开销
4. **循环引用必须用 weak_ptr 打破**：这是 shared_ptr 最常见的泄漏场景
5. **返回类型匹配所有权语义**：不拥有就别返回智能指针
6. **用 `make_unique`/`make_shared` 代替 `new`**：异常安全 + 性能更好

## 文件结构

```
smart_pointer/
├── smart_pointer_demo.cpp   # 全部5个场景的单文件演示
├── CMakeLists.txt            # CMake 构建配置
└── README.md                 # 本文件
```
