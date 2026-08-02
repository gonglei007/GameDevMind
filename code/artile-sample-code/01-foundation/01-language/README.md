# 01-language — 编程语言性能对比

配套文章：一-01 编程语言全解析

## 文件

| 文件 | 说明 |
|------|------|
| `language_comparison.py` | C++ vs C# vs Python 游戏性能对比 benchmark |

## 运行

```bash
python3 language_comparison.py
```

纯标准库，无外部依赖。

## Benchmark 项目

1. **循环密集计算** — 模拟游戏主循环中实体 Update 遍历
2. **数学运算吞吐** — 模拟物理计算和顶点变换
3. **内存访问模式** — 缓存友好 (row-major) vs 缓存不友好 (col-major)

## 要点

- Python 适合工具链和原型，不适合热路径
- C# 通过值类型和 JIT 可接近 C++ 性能
- C++ 对内存布局有完全控制，SoA + SIMD 优势巨大
