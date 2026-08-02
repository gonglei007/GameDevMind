"""
四叉树 (Quadtree) — 游戏空间分区

对应文章：一-03-数据结构与算法

场景：开放世界游戏中，需要快速查询「玩家周围 50 米内所有敌人」。
暴力遍历 O(N)，四叉树降至 O(log N)。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import random


@dataclass
class Rect:
    """轴对齐矩形"""
    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        return (self.x - self.w <= px <= self.x + self.w and
                self.y - self.h <= py <= self.y + self.h)

    def intersects(self, other: "Rect") -> bool:
        return not (self.x - self.w > other.x + other.w or
                    self.x + self.w < other.x - other.w or
                    self.y - self.h > other.y + other.h or
                    self.y + self.h < other.y - other.h)


@dataclass
class Entity:
    """游戏实体"""
    id: int
    x: float
    y: float
    name: str = ""

    @property
    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)


class Quadtree:
    """四叉树空间索引"""

    MAX_OBJECTS = 4   # 每个节点最多存 4 个对象
    MAX_LEVELS = 5    # 最大深度

    def __init__(self, level: int, bounds: Rect):
        self.level = level
        self.bounds = bounds
        self.objects: List[Entity] = []
        self.nodes: List[Optional["Quadtree"]] = [None] * 4  # NW, NE, SW, SE

    def clear(self):
        self.objects.clear()
        for i in range(4):
            if self.nodes[i]:
                self.nodes[i].clear()
                self.nodes[i] = None

    def _split(self):
        """分裂为 4 个子节点"""
        sub_w = self.bounds.w / 2
        sub_h = self.bounds.h / 2
        x, y = self.bounds.x, self.bounds.y

        self.nodes[0] = Quadtree(self.level + 1, Rect(x - sub_w, y - sub_h, sub_w, sub_h))  # NW
        self.nodes[1] = Quadtree(self.level + 1, Rect(x + sub_w, y - sub_h, sub_w, sub_h))  # NE
        self.nodes[2] = Quadtree(self.level + 1, Rect(x - sub_w, y + sub_h, sub_w, sub_h))  # SW
        self.nodes[3] = Quadtree(self.level + 1, Rect(x + sub_w, y + sub_h, sub_w, sub_h))  # SE

    def _get_index(self, entity: Entity) -> int:
        """确定实体属于哪个子节点 (-1 表示跨边界)"""
        x, y = entity.x, entity.y
        mid_x, mid_y = self.bounds.x, self.bounds.y

        top = y < mid_y
        bottom = y > mid_y
        left = x < mid_x
        right = x > mid_x

        if left and top:
            return 0
        if right and top:
            return 1
        if left and bottom:
            return 2
        if right and bottom:
            return 3
        return -1  # 跨边界，留在当前节点

    def insert(self, entity: Entity):
        """插入实体"""
        # 如果有子节点
        if self.nodes[0]:
            idx = self._get_index(entity)
            if idx != -1:
                self.nodes[idx].insert(entity)
                return

        self.objects.append(entity)

        # 超出容量则分裂
        if len(self.objects) > self.MAX_OBJECTS and self.level < self.MAX_LEVELS:
            if not self.nodes[0]:
                self._split()

            # 重新分配当前对象
            remaining = []
            for obj in self.objects:
                idx = self._get_index(obj)
                if idx != -1:
                    self.nodes[idx].insert(obj)
                else:
                    remaining.append(obj)
            self.objects = remaining

    def query(self, range_rect: Rect) -> List[Entity]:
        """查询范围内的所有实体"""
        result = []

        if not self.bounds.intersects(range_rect):
            return result

        for obj in self.objects:
            if range_rect.contains(obj.x, obj.y):
                result.append(obj)

        if self.nodes[0]:
            for node in self.nodes:
                result.extend(node.query(range_rect))

        return result

    def print_structure(self, indent: str = ""):
        """打印树结构（调试用）"""
        print(f"{indent}Lv{self.level} [{self.bounds.x:.0f},{self.bounds.y:.0f}] "
              f"objects={len(self.objects)}")
        if self.nodes[0]:
            for i, node in enumerate(self.nodes):
                if node and (node.objects or node.nodes[0]):
                    node.print_structure(indent + "  ")


# ============================================================
# 演示：游戏中"查询玩家周围敌人"
# ============================================================
def main():
    print("=== 四叉树演示（空间查询）===\n")

    # 创建 1000x1000 的游戏世界
    world = Rect(500, 500, 500, 500)
    tree = Quadtree(0, world)

    # 生成 100 个随机敌人
    random.seed(42)
    enemies = []
    for i in range(100):
        e = Entity(
            id=i,
            x=random.uniform(0, 1000),
            y=random.uniform(0, 1000),
            name=f"敌人_{i}"
        )
        enemies.append(e)
        tree.insert(e)

    # 玩家位置
    player_x, player_y = 500, 500
    search_range = Rect(player_x, player_y, 100, 100)

    # 四叉树查询
    nearby = tree.query(search_range)
    print(f"🎯 玩家在 ({player_x}, {player_y})，查询半径 100")
    print(f"📊 四叉树查询结果: {len(nearby)} 个敌人")
    print(f"   暴力遍历对照: {sum(1 for e in enemies if search_range.contains(e.x, e.y))} 个")
    print(f"   四叉树仅检查了局部节点，避免遍历全部 {len(enemies)} 个实体\n")

    # 显示树结构
    print("🌳 四叉树结构：")
    tree.print_structure()

    print("\n✅ 四叉树演示完成")


if __name__ == "__main__":
    main()
