# 02-physics — Verlet 积分粒子 + AABB 碰撞模拟

> 对应文章：二-02 物理系统

> 正文已瘦身：Verlet + AABB 完整演示见 `physics_demo.py`，文章保留概念与优化 checklist。

## 运行

```bash
python physics_demo.py
```

纯标准库，无需安装任何依赖。

## 功能

- **Verlet 积分器**：位置驱动，无需显式存储速度（速度由 `pos - prev_pos` 隐式表达），天然稳定
- **AABB 碰撞检测**：轴对齐包围盒快速重叠测试
- **MTV 分离**：最小分离向量驱动碰撞响应，按质量比分配位移
- **静态碰撞体**：平台、地面等不可动物体
- **边界约束**：弹性边界反弹
- **子步骤**：每帧 4 次子步提高积分精度

## 核心概念

| 概念 | 实现 |
|------|------|
| Verlet 积分 | `pos_new = pos + (pos - prev_pos) * damping + gravity * dt²` |
| AABB 重叠 | 4 个一维区间测试 |
| MTV (最小分离向量) | X/Y 轴穿透深度取最小 |
| 碰撞响应 | 位置修正 + 速度方向反弹 |
| 质量比 | 碰撞位移按 `mass_other / total_mass` 分配 |

## 与真实物理引擎对比

本 demo 是一个教学简化版，真实引擎（Box2D、PhysX）在此之上增加了：
- 旋转刚体 + 惯性张量
- 连续碰撞检测 (CCD)
- 约束求解器 (关节、铰链)
- 空间划分 (BVH、网格)

## 可调参数

在 `PhysicsWorld.__init__()` 和 `main()` 中可调整：
- `gravity`：重力向量（默认向下 0.5）
- `damping`：阻尼系数（默认 0.995）
- `substeps`：每帧子步数（默认 4）
- 粒子数量、初始速度、平台位置
