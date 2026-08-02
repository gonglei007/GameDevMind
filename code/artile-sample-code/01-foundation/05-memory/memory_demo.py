"""
内存布局优化 — AoS vs SoA + 自定义分配器

对应文章：一-05-内存管理深度解析

游戏中每秒更新数万个实体，内存访问模式直接影响性能。
Array of Structures (AoS) vs Structure of Arrays (SoA) 的区别可达 3-5x。
"""

import time
import random
import struct
from dataclasses import dataclass
from typing import List


# ============================================================
# 1. AoS vs SoA 性能对比
# ============================================================

@dataclass
class ParticleAoS:
    """Array of Structures — 每个粒子存自己的 x, y, vx, vy, life"""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 1.0


@dataclass
class ParticleSystemSoA:
    """Structure of Arrays — 所有粒子的 x 在一起，y 在一起..."""
    xs: List[float]
    ys: List[float]
    vxs: List[float]
    vys: List[float]
    lives: List[float]
    count: int = 0

    @classmethod
    def create(cls, n: int):
        return cls(
            xs=[0.0] * n,
            ys=[0.0] * n,
            vxs=[0.0] * n,
            vys=[0.0] * n,
            lives=[0.0] * n,
            count=n
        )

    def update(self):
        """更新所有粒子 — CPU 缓存友好的顺序访问"""
        for i in range(self.count):
            if self.lives[i] <= 0:
                continue
            self.xs[i] += self.vxs[i]
            self.ys[i] += self.vys[i]
            self.lives[i] -= 0.016  # ~60fps delta


# ============================================================
# 2. 简单的池分配器（固定大小块）
# ============================================================

class PoolAllocator:
    """
    游戏中的池分配器：预先分配一块内存，循环复用。
    避免频繁 malloc/free 导致的内存碎片。
    """

    def __init__(self, item_size: int, capacity: int):
        self.item_size = item_size
        self.capacity = capacity
        self._data = bytearray(item_size * capacity)
        self._free_list = list(range(capacity - 1, -1, -1))  # 栈：后进先出
        self._allocated = 0

    def alloc(self) -> int:
        """返回槽位索引"""
        if not self._free_list:
            raise MemoryError("PoolAllocator exhausted")
        self._allocated += 1
        return self._free_list.pop()

    def free(self, index: int):
        self._free_list.append(index)
        self._allocated -= 1

    @property
    def usage(self) -> float:
        return self._allocated / self.capacity


# ============================================================
# 3. ECS 风格的实体存储（简化版）
# ============================================================

class ComponentStore:
    """按组件类型列式存储 — 现代 ECS 引擎的核心思想"""
    def __init__(self, capacity: int = 10000):
        self._position_x = [0.0] * capacity
        self._position_y = [0.0] * capacity
        self._velocity_x = [0.0] * capacity
        self._velocity_y = [0.0] * capacity
        self._hp = [100] * capacity
        self._active = [False] * capacity
        self._count = 0

    def spawn(self, x: float, y: float, vx: float, vy: float, hp: int) -> int:
        idx = self._count
        self._position_x[idx] = x
        self._position_y[idx] = y
        self._velocity_x[idx] = vx
        self._velocity_y[idx] = vy
        self._hp[idx] = hp
        self._active[idx] = True
        self._count += 1
        return idx

    def move_system(self):
        """Movement System：只访问 position 和 velocity 数组"""
        for i in range(self._count):
            if not self._active[i]:
                continue
            self._position_x[i] += self._velocity_x[i]
            self._position_y[i] += self._velocity_y[i]

    def damage_system(self, amount: int):
        """Damage System：只访问 hp 数组"""
        for i in range(self._count):
            if not self._active[i]:
                continue
            self._hp[i] -= amount

    def alive_count(self) -> int:
        return sum(1 for i in range(self._count)
                   if self._active[i] and self._hp[i] > 0)


# ============================================================
# 演示
# ============================================================

def benchmark_aos_vs_soa():
    N = 100_000
    dt = 0.016

    # AoS
    particles = [ParticleAoS(random.uniform(0, 100), random.uniform(0, 100),
                              random.uniform(-1, 1), random.uniform(-1, 1))
                 for _ in range(N)]

    start = time.perf_counter()
    for p in particles:
        if p.life > 0:
            p.x += p.vx * dt
            p.y += p.vy * dt
    aos_time = time.perf_counter() - start

    # SoA
    system = ParticleSystemSoA.create(N)
    for i in range(N):
        system.xs[i] = random.uniform(0, 100)
        system.ys[i] = random.uniform(0, 100)
        system.vxs[i] = random.uniform(-1, 1)
        system.vys[i] = random.uniform(-1, 1)
        system.lives[i] = 1.0

    start = time.perf_counter()
    system.update()
    soa_time = time.perf_counter() - start

    return aos_time, soa_time


def main():
    print("=== 游戏内存管理演示 ===\n")

    # 1. AoS vs SoA
    print("📊 AoS vs SoA 性能对比 (100,000 粒子 × 1 帧)")
    aos, soa = benchmark_aos_vs_soa()
    print(f"  AoS (Array of Structures): {aos*1000:.2f} ms")
    print(f"  SoA (Structure of Arrays): {soa*1000:.2f} ms")
    print(f"  SoA 快 {aos/soa:.1f}x  — 连续内存访问命中 CPU 缓存行\n")

    # 2. 池分配器
    print("🗂️  池分配器演示")
    pool = PoolAllocator(item_size=64, capacity=10)
    print(f"  容量: {pool.capacity}, 使用率: {pool.usage:.0%}")
    slots = [pool.alloc() for _ in range(5)]
    print(f"  分配 5 个槽位: {slots}")
    print(f"  使用率: {pool.usage:.0%}")
    for s in slots[:3]:
        pool.free(s)
    print(f"  释放 3 个后使用率: {pool.usage:.0%}")
    new_slot = pool.alloc()
    print(f"  再次分配: 槽位 {new_slot}（复用已释放的槽位）\n")

    # 3. ECS 列式存储
    print("🧩 ECS 列式存储演示")
    store = ComponentStore(100)
    store.spawn(0, 0, 1, 0.5, 100)
    store.spawn(10, 5, -0.5, 1, 80)
    store.spawn(20, 10, 0.5, -0.5, 60)
    print(f"  生成 3 个实体")
    for _ in range(10):
        store.move_system()
    print(f"  10 帧后位置: ({store._position_x[0]:.0f}, {store._position_y[0]:.0f})")
    store.damage_system(30)
    print(f"  受到 30 伤害后存活: {store.alive_count()}/3")

    print("\n✅ 内存管理演示完成")


if __name__ == "__main__":
    main()
