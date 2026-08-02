"""
游戏事件系统 — 观察者模式实现

对应文章：一-02-设计模式实战 / 一-03-数据结构与算法

游戏中最常用的观察者模式变体：EventBus / 信号槽
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any
from enum import Enum, auto


# ============================================================
# 1. 简单事件总线
# ============================================================
class EventBus:
    """轻量级游戏事件系统"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        """订阅事件"""
        self._handlers.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable):
        """取消订阅"""
        if event in self._handlers:
            self._handlers[event] = [
                h for h in self._handlers[event] if h != callback
            ]

    def emit(self, event: str, **kwargs):
        """触发事件"""
        for handler in self._handlers.get(event, []):
            handler(kwargs)


# ============================================================
# 2. 游戏事件示例
# ============================================================
@dataclass
class GameEvent:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)


class Player:
    def __init__(self, name: str, hp: int = 100):
        self.name = name
        self.hp = hp
        self._max_hp = hp

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def hp_ratio(self) -> float:
        return self.hp / self._max_hp


# 各个系统的响应函数
def on_player_hit(data: dict):
    print(f"  🎯 命中反馈：{data['attacker']} 对 {data['target']} 造成 {data['damage']} 点伤害")

def on_player_death(data: dict):
    print(f"  💀 死亡事件：{data['name']} 已阵亡，掉落物品 x{data['drop_count']}")

def on_score_changed(data: dict):
    print(f"  ⭐ 分数变化：+{data['delta']}，总分 {data['total']}")

def on_achievement(data: dict):
    print(f"  🏆 成就解锁：{data['name']} — {data['desc']}")


# ============================================================
# 3. 演示
# ============================================================
def main():
    bus = EventBus()

    # 注册监听
    bus.on("player:hit", on_player_hit)
    bus.on("player:death", on_player_death)
    bus.on("score:changed", on_score_changed)
    bus.on("achievement:unlocked", on_achievement)

    # 模拟游戏流程
    print("=== 游戏事件系统演示 ===\n")

    print("[关卡开始]")
    bus.emit("player:hit", attacker="哥布林", target="英雄", damage=15)
    bus.emit("score:changed", delta=100, total=150)

    print("\n[击败 Boss]")
    bus.emit("score:changed", delta=500, total=650)
    bus.emit("achievement:unlocked", name="初出茅庐", desc="首次击败 Boss")

    print("\n[主角阵亡]")
    bus.emit("player:death", name="英雄", drop_count=3)

    print("\n✅ 事件系统演示完成")

    # 验证取消订阅
    bus.off("player:hit", on_player_hit)
    print(f"\n[取消订阅后] player:hit 监听者数量: {len(bus._handlers.get('player:hit', []))}")


if __name__ == "__main__":
    main()
