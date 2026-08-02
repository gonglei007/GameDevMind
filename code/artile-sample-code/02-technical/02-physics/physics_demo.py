#!/usr/bin/env python3
"""
Verlet 积分粒子系统 + AABB 碰撞 + 重力模拟

纯标准库实现，模拟物理引擎核心：
1. Verlet 积分 — 无需显式存储速度，由当前位置和上一帧位置推导
2. AABB 轴对齐包围盒碰撞检测与响应
3. 约束求解 — 地面碰撞、边界约束
4. 简单重力 + 阻尼

运行：python physics_demo.py
"""

import math
import random
import time
import sys


# ──────────────────────────────────────────────
# 向量工具
# ──────────────────────────────────────────────


class Vec2:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def __add__(self, o):
        return Vec2(self.x + o.x, self.y + o.y)

    def __sub__(self, o):
        return Vec2(self.x - o.x, self.y - o.y)

    def __mul__(self, s):
        return Vec2(self.x * s, self.y * s)

    def __truediv__(self, s):
        return Vec2(self.x / s, self.y / s) if s != 0 else Vec2()

    def __neg__(self):
        return Vec2(-self.x, -self.y)

    def dot(self, o):
        return self.x * o.x + self.y * o.y

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self):
        l = self.length()
        return self / l if l > 1e-8 else Vec2()

    def __repr__(self):
        return f"({self.x:.2f}, {self.y:.2f})"


# ──────────────────────────────────────────────
# AABB 包围盒
# ──────────────────────────────────────────────


class AABB:
    """轴对齐包围盒"""
    __slots__ = ("min", "max")

    def __init__(self, center, half_size):
        self.min = center - half_size
        self.max = center + half_size

    @staticmethod
    def overlap(a, b):
        """检测两个 AABB 是否重叠"""
        return (
            a.min.x < b.max.x
            and a.max.x > b.min.x
            and a.min.y < b.max.y
            and a.max.y > b.min.y
        )

    @staticmethod
    def penetration(a, b):
        """计算最小分离向量 (MTV)"""
        overlap_x = min(a.max.x - b.min.x, b.max.x - a.min.x)
        overlap_y = min(a.max.y - b.min.y, b.max.y - a.min.y)

        if overlap_x < overlap_y:
            # X 轴分离
            direction = 1.0 if a.max.x - b.min.x < b.max.x - a.min.x else -1.0
            return Vec2(overlap_x * direction, 0.0)
        else:
            direction = 1.0 if a.max.y - b.min.y < b.max.y - a.min.y else -1.0
            return Vec2(0.0, overlap_y * direction)


# ──────────────────────────────────────────────
# Verlet 粒子
# ──────────────────────────────────────────────


class Particle:
    """Verlet 积分粒子 — 位置 + 上一帧位置 (速度隐含)"""
    __slots__ = ("pos", "prev_pos", "radius", "mass", "color_char", "id")

    _next_id = 0

    def __init__(self, position, velocity=Vec2(), radius=1.0, mass=1.0, color_char="●"):
        self.pos = position
        # Verlet: prev_pos = pos - velocity * dt (假设 dt=1)
        self.prev_pos = position - velocity
        self.radius = radius
        self.mass = mass
        self.color_char = color_char
        self.id = Particle._next_id
        Particle._next_id += 1

    def velocity(self):
        """从 Verlet 积分还原速度"""
        return self.pos - self.prev_pos

    def get_aabb(self):
        hs = Vec2(self.radius, self.radius)
        return AABB(self.pos, hs)


# ──────────────────────────────────────────────
# 物理世界
# ──────────────────────────────────────────────


class PhysicsWorld:
    def __init__(self, gravity=0.5, damping=0.99, bounds=None):
        self.gravity = Vec2(0.0, gravity)
        self.damping = damping
        self.bounds = bounds or AABB(Vec2(0, 0), Vec2(50, 25))  # 默认边界
        self.particles = []
        self.static_bodies = []  # 静态碰撞体 (AABB 列表)
        self.substeps = 4  # 子步骤提高精度

    def add_particle(self, particle):
        self.particles.append(particle)

    def add_static_body(self, aabb):
        self.static_bodies.append(aabb)

    def step(self, dt=1.0):
        """单步物理模拟"""
        sub_dt = dt / self.substeps

        for _ in range(self.substeps):
            # 1. Verlet 积分 (所有粒子)
            for p in self.particles:
                velocity = p.velocity() * self.damping
                p.prev_pos = Vec2(p.pos.x, p.pos.y)  # 保存当前位置
                p.pos = p.pos + velocity + self.gravity * (sub_dt * sub_dt)

            # 2. 粒子间 AABB 碰撞
            for i in range(len(self.particles)):
                for j in range(i + 1, len(self.particles)):
                    self._resolve_particle_collision(
                        self.particles[i], self.particles[j]
                    )

            # 3. 粒子与静态体碰撞
            for p in self.particles:
                for body in self.static_bodies:
                    self._resolve_static_collision(p, body)

            # 4. 边界约束
            for p in self.particles:
                self._constrain_to_bounds(p)

    def _resolve_particle_collision(self, a, b):
        """粒子间 AABB 碰撞响应 (位置修正)"""
        box_a = a.get_aabb()
        box_b = b.get_aabb()

        if not AABB.overlap(box_a, box_b):
            return

        mtv = AABB.penetration(box_a, box_b)
        total_mass = a.mass + b.mass

        # 按质量比分配位移
        ratio_a = b.mass / total_mass if total_mass > 0 else 0.5
        ratio_b = a.mass / total_mass if total_mass > 0 else 0.5

        a.pos = a.pos + mtv * ratio_a
        b.pos = b.pos - mtv * ratio_b

    def _resolve_static_collision(self, p, body):
        """粒子与静态 AABB 碰撞"""
        box_p = p.get_aabb()
        if not AABB.overlap(box_p, body):
            return

        mtv = AABB.penetration(box_p, body)
        p.pos = p.pos + mtv

        # 速度响应：沿 MTV 方向反弹 (简单系数)
        vel = p.velocity()
        mtv_dir = mtv.normalized()
        # 仅当速度朝向碰撞面时反弹
        proj = vel.dot(mtv_dir)
        if proj < 0:
            # 修改 prev_pos 实现反弹 (restitution ≈ 0.3)
            p.prev_pos = p.prev_pos + mtv_dir * (proj * 1.3)

    def _constrain_to_bounds(self, p):
        """边界约束"""
        r = p.radius
        margin = 0.0
        b = self.bounds

        if p.pos.x - r < b.min.x + margin:
            p.pos.x = b.min.x + r + margin
            p.prev_pos.x = p.pos.x + abs(p.velocity().x) * 0.3
        elif p.pos.x + r > b.max.x - margin:
            p.pos.x = b.max.x - r - margin
            p.prev_pos.x = p.pos.x - abs(p.velocity().x) * 0.3

        if p.pos.y - r < b.min.y + margin:
            p.pos.y = b.min.y + r + margin
            p.prev_pos.y = p.pos.y + abs(p.velocity().y) * 0.3
        elif p.pos.y + r > b.max.y - margin:
            p.pos.y = b.max.y - r - margin
            p.prev_pos.y = p.pos.y - abs(p.velocity().y) * 0.3


# ──────────────────────────────────────────────
# ASCII 可视化
# ──────────────────────────────────────────────


class AsciiRenderer:
    def __init__(self, width=80, height=30):
        self.width = width
        self.height = height
        self.world_bounds = AABB(Vec2(0, 0), Vec2(50, 25))

    def world_to_screen(self, world_pos):
        """世界坐标 → 屏幕坐标"""
        w = self.world_bounds.max.x - self.world_bounds.min.x
        h = self.world_bounds.max.y - self.world_bounds.min.y
        x = int((world_pos.x - self.world_bounds.min.x) / w * (self.width - 1))
        y = int((1 - (world_pos.y - self.world_bounds.min.y) / h) * (self.height - 1))
        return max(0, min(self.width - 1, x)), max(0, min(self.height - 1, y))

    def render(self, world):
        """渲染一帧为字符串"""
        grid = [[" "] * self.width for _ in range(self.height)]

        # 绘制静态体
        for body in world.static_bodies:
            tl = self.world_to_screen(Vec2(body.min.x, body.max.y))
            br = self.world_to_screen(Vec2(body.max.x, body.min.y))
            for y in range(tl[1], br[1] + 1):
                for x in range(tl[0], br[0] + 1):
                    if 0 <= y < self.height and 0 <= x < self.width:
                        grid[y][x] = "█"

        # 绘制粒子
        for p in world.particles:
            sx, sy = self.world_to_screen(p.pos)
            if 0 <= sy < self.height and 0 <= sx < self.width:
                grid[sy][sx] = p.color_char

        # 绘制边界
        for x in range(self.width):
            grid[0][x] = "─"
            grid[self.height - 1][x] = "─"
        for y in range(self.height):
            grid[y][0] = "│"
            grid[y][self.width - 1] = "│"
        grid[0][0] = "┌"
        grid[0][self.width - 1] = "┐"
        grid[self.height - 1][0] = "└"
        grid[self.height - 1][self.width - 1] = "┘"

        return "\n".join("".join(row) for row in grid)


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  Verlet 积分粒子系统 + AABB 碰撞 + 重力模拟")
    print("=" * 60)
    print()

    # 物理世界 (重力向下 0.5, 阻尼 0.99)
    world = PhysicsWorld(gravity=0.5, damping=0.995)

    # 添加静态体 — 地面平台
    # 中间平台
    world.add_static_body(AABB(Vec2(15, 15), Vec2(10, 1)))
    # 右侧平台
    world.add_static_body(AABB(Vec2(35, 10), Vec2(8, 1)))
    # 左侧小平台
    world.add_static_body(AABB(Vec2(5, 20), Vec2(5, 1)))

    # 添加粒子 — 随机初始位置和速度
    random.seed(42)
    colors = ["●", "○", "◆", "◇", "★", "☆", "▲", "△"]
    for i in range(15):
        pos = Vec2(random.uniform(2, 48), random.uniform(18, 24))
        vel = Vec2(random.uniform(-3, 3), random.uniform(-5, -1))
        p = Particle(
            position=pos,
            velocity=vel,
            radius=0.5,
            mass=random.uniform(0.5, 2.0),
            color_char=colors[i % len(colors)],
        )
        world.add_particle(p)

    renderer = AsciiRenderer(80, 30)
    renderer.world_bounds = world.bounds

    print("【初始状态】")
    print(f"  粒子数: {len(world.particles)}")
    print(f"  静态碰撞体: {len(world.static_bodies)} 个平台")
    print(f"  重力: {world.gravity.y} 单位/帧²")
    print(f"  积分器: Verlet (4 子步骤/帧)")
    print()

    # 模拟帧
    frames_to_simulate = 6
    for frame in range(frames_to_simulate):
        for _ in range(5):  # 每"显示帧"做 5 个物理步
            world.step(dt=1.0)

        print(f"\n{'─' * 60}")
        print(f"  帧 {frame + 1}/{frames_to_simulate}")
        print(f"{'─' * 60}")
        print(renderer.render(world))

        # 打印粒子统计
        total_ke = sum(p.velocity().length() ** 2 * p.mass for p in world.particles) * 0.5
        avg_y = sum(p.pos.y for p in world.particles) / len(world.particles)
        print(f"  总动能: {total_ke:.1f} | 平均高度: {avg_y:.1f}")

        time.sleep(0.3)

    print()
    print("=" * 60)
    print("  模拟完成！")
    print("  核心算法: Verlet 积分 → AABB 重叠检测 → MTV 分离")
    print("=" * 60)


if __name__ == "__main__":
    main()
