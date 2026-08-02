#!/usr/bin/env python3
"""
编程语言性能对比 Demo —— 模拟 C++ / C# / Python 在游戏场景下的性能特征

对应文章：../../游戏开发图谱/基础能力篇/一-01-游戏开发该学什么语言？C++／C#／JS 全面对比，选对效率翻倍.md

本脚本用纯 Python 实现基准测试，模拟三种语言在以下场景的典型表现：
  1. 循环密集计算（模拟游戏主循环中的实体更新）
  2. 数学运算吞吐（物理计算 & 顶点变换）
  3. 内存访问模式（缓存友好 vs 缓存不友好）

注意：C++/C# 的数据是近似参考值（基于典型 benchmark 数据），Python 数据为实测。
"""

import time
import math
import random
import sys


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark 1：循环密集计算 —— 模拟游戏主循环中 N 个实体的 Update()
# ═══════════════════════════════════════════════════════════════════════════════

def benchmark_loop_overhead(iterations: int = 10_000_000) -> dict:
    """
    纯粹的空循环开销测试。
    游戏主循环每帧要遍历大量实体，循环本身的开销是关键指标。

    Python:    由于解释执行，每次迭代都有字节码 dispatch 开销，约 50-100 ns/iter
    C#:        JIT 编译后循环体可被优化，约 5-10 ns/iter (Release 模式)
    C++:       编译器可完全消除空循环或降至 ~1 ns/iter (-O2 下)
    """
    # --- Python 实测 ---
    start = time.perf_counter()
    for _ in range(iterations):
        pass
    elapsed_py = time.perf_counter() - start

    # --- 参考近似值（基于典型 i7-13700K 数据） ---
    cpp_ns_per_iter = 1.0       # C++ -O2 空循环
    cs_ns_per_iter  = 5.0       # C# Release 空循环
    py_ns_per_iter  = (elapsed_py / iterations) * 1e9

    return {
        "test": "空循环遍历 (10M 次)",
        "python_actual": f"{elapsed_py:.4f}s ({py_ns_per_iter:.1f} ns/iter)",
        "cpp_approx":    f"~{cpp_ns_per_iter * iterations / 1e9:.4f}s ({cpp_ns_per_iter:.0f} ns/iter)",
        "csharp_approx": f"~{cs_ns_per_iter * iterations / 1e9:.4f}s ({cs_ns_per_iter:.0f} ns/iter)",
        "python_vs_cpp": f"{py_ns_per_iter / cpp_ns_per_iter:.0f}x slower",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark 2：数学运算吞吐 —— 模拟物理 / 顶点变换
# ═══════════════════════════════════════════════════════════════════════════════

def benchmark_math_throughput(iterations: int = 2_000_000) -> dict:
    """
    密集数学运算：sin/cos + 乘加混合（模拟骨骼动画的顶点蒙皮计算）。

    Python:    math.sin 底层调用 C 的 libm，相对不慢，但 Python 层的循环开销主导
    C#:        System.Math.Sin 也是 JIT intrinsic，接近 C 速度
    C++:       编译器可能将 sin/cos 向量化 (SIMD)，吞吐极高
    """
    # --- Python 实测 ---
    result = 0.0
    start = time.perf_counter()
    for i in range(iterations):
        x = float(i) * 0.001
        result += math.sin(x) * math.cos(x * 1.1) + math.sqrt(abs(x) + 0.1)
    elapsed_py = time.perf_counter() - start

    # 防优化消除
    if result < 0:
        print(result)

    return {
        "test": "密集数学运算 (2M 次 sin/cos/sqrt)",
        "python_actual": f"{elapsed_py:.4f}s",
        "cpp_approx":    f"~{elapsed_py * 0.03:.4f}s (约 30x 快于 Python)",
        "csharp_approx": f"~{elapsed_py * 0.06:.4f}s (约 15x 快于 Python)",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark 3：内存访问模式 —— 缓存友好 vs 缓存不友好
# ═══════════════════════════════════════════════════════════════════════════════

def benchmark_memory_access(size: int = 4096) -> dict:
    """
    模拟 ECS 组件数组的顺序访问 vs 随机访问。

    游戏数据布局至关重要：
    - SoA (Structure of Arrays) → 顺序访问，缓存命中率高
    - AoS (Array of Structures) → 跨步访问，缓存未命中

    Python 中 list-of-objects 天生是 AoS（指针追踪），
    C++ 中可通过 std::vector<float> 实现 SoA。
    """
    # 构造一个 2D 数组模拟组件数据
    matrix = [[random.random() for _ in range(size)] for _ in range(size)]

    # --- 顺序访问 (缓存友好) ---
    total = 0.0
    start = time.perf_counter()
    for row in range(size):
        for col in range(size):
            total += matrix[row][col]
    seq_time = time.perf_counter() - start

    # --- 跨步访问 (缓存不友好：按列遍历) ---
    total = 0.0
    start = time.perf_counter()
    for col in range(size):
        for row in range(size):
            total += matrix[row][col]
    stride_time = time.perf_counter() - start

    if total < 0:
        print(total)

    return {
        "test": f"内存访问模式 ({size}x{size} 矩阵)",
        "python_seq (row-major, cache-friendly)": f"{seq_time:.4f}s",
        "python_stride (col-major, cache-hostile)": f"{stride_time:.4f}s",
        "slowdown_ratio": f"{stride_time / seq_time:.2f}x",
        "note": "C++ 中 SoA 布局可让顺序访问再快 5-10x，跨步访问差距更大",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main 演示入口
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("  游戏编程语言性能对比 Benchmark")
    print("  C++ / C# / Python — 模拟游戏负载场景")
    print("=" * 72)
    print(f"  Python 版本: {sys.version}")
    print()

    results = []

    print("[1/3] 循环密集计算（模拟实体 Update 遍历）...")
    results.append(benchmark_loop_overhead())

    print("[2/3] 数学运算吞吐（模拟物理 / 顶点变换）...")
    results.append(benchmark_math_throughput())

    print("[3/3] 内存访问模式（缓存友好 vs 不友好）...")
    results.append(benchmark_memory_access())

    print()
    print("=" * 72)
    print("  结果汇总")
    print("=" * 72)
    for r in results:
        print(f"\n  ▶ {r['test']}")
        for k, v in r.items():
            if k != "test":
                print(f"      {k}: {v}")

    print()
    print("=" * 72)
    print("  结论")
    print("=" * 72)
    print("""
  1. Python 在循环和内存访问上远慢于 C++/C#，适合做工具链和原型，不适合热路径。
  2. C# 通过 JIT + 值类型 (struct) 可接近 C++ 性能，Unity 的 Burst Compiler 进一步缩小差距。
  3. C++ 对内存布局有完全控制，SoA + SIMD 在批量处理上优势巨大。
  4. 现代游戏引擎通常用 C++ 写核心，Python/Lua 做脚本层。
""")


if __name__ == "__main__":
    main()
