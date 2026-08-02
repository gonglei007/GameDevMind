#!/usr/bin/env python3
"""
战斗系统演示：伤害公式完整链路
纯标准库，直接运行。

伤害计算链：
  1. 基础攻击力 → 技能倍率
  2. 防御减免：DEF / (DEF + 100)
  3. 暴击判定：CRIT% 概率
  4. 元素克制：火>草>水>火 (1.5x / 0.75x)
  5. 伤害浮动：±10% 随机
  6. 最终伤害钳制
"""

import random
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── 元素类型 ─────────────────────────────────────────────────────
class Element(Enum):
    NONE = 0
    FIRE = 1
    WATER = 2
    GRASS = 3
    LIGHT = 4
    DARK = 5


# 元素克制表：attacker → defender → 倍率
ELEMENT_ADVANTAGE: dict[tuple[Element, Element], float] = {
    (Element.FIRE, Element.GRASS): 1.5,
    (Element.WATER, Element.FIRE): 1.5,
    (Element.GRASS, Element.WATER): 1.5,
    (Element.LIGHT, Element.DARK): 1.3,
    (Element.DARK, Element.LIGHT): 1.3,
}

ELEMENT_DISADVANTAGE: dict[tuple[Element, Element], float] = {
    (Element.FIRE, Element.WATER): 0.75,
    (Element.WATER, Element.GRASS): 0.75,
    (Element.GRASS, Element.FIRE): 0.75,
}


def get_element_multiplier(atk_element: Element, def_element: Element) -> float:
    """获取元素克制倍率"""
    if atk_element == Element.NONE or def_element == Element.NONE:
        return 1.0
    key = (atk_element, def_element)
    if key in ELEMENT_ADVANTAGE:
        return ELEMENT_ADVANTAGE[key]
    if key in ELEMENT_DISADVANTAGE:
        return ELEMENT_DISADVANTAGE[key]
    return 1.0


# ─── 战斗单位 ─────────────────────────────────────────────────────
@dataclass
class CombatUnit:
    name: str
    atk: float = 100       # 攻击力
    defense: float = 50    # 防御力
    hp: float = 1000       # 生命值
    crit_rate: float = 10  # 暴击率 (%)
    crit_dmg: float = 150  # 暴击伤害 (%)
    element: Element = Element.NONE

    speed: float = 100     # 速度（决定行动顺序）

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, damage: float) -> str:
        self.hp = max(0, self.hp - damage)
        return f"{'💀' if self.hp == 0 else '❤️'} {self.name} 剩余 HP: {self.hp:.0f}"


# ─── 伤害计算器 ──────────────────────────────────────────────────
@dataclass
class DamageResult:
    """伤害计算结果明细"""
    raw_damage: float = 0       # 技能原始伤害
    def_reduction: float = 0    # 防御减免
    after_def: float = 0        # 防御减免后
    is_crit: bool = False       # 是否暴击
    crit_mult: float = 1.0      # 暴击倍率
    after_crit: float = 0       # 暴击后
    element_mult: float = 1.0   # 元素克制倍率
    after_element: float = 0    # 元素后
    variance: float = 1.0       # 浮动倍率
    final_damage: float = 0     # 最终伤害

    def print(self):
        print("  ┌────────── 伤害明细 ──────────┐")
        print(f"  │ 技能原始伤害:    {self.raw_damage:>10.1f} │")
        print(f"  │ 防御减免:        {self.def_reduction:>10.1f} │")
        print(f"  │ 防御后伤害:      {self.after_def:>10.1f} │")
        print(f"  │ 暴击: {'✅ 是' if self.is_crit else '❌ 否':>14s} x{self.crit_mult:.2f} │")
        print(f"  │ 暴击后伤害:      {self.after_crit:>10.1f} │")
        print(f"  │ 元素倍率:        x{self.element_mult:.2f}     │")
        print(f"  │ 元素后伤害:      {self.after_element:>10.1f} │")
        print(f"  │ 浮动倍率:        x{self.variance:.2f}     │")
        print(f"  │ ▶ 最终伤害:      {self.final_damage:>10.1f} ◀│")
        print("  └───────────────────────────────┘")


class DamageCalculator:
    """伤害公式计算器"""

    DAMAGE_VARIANCE = 0.1  # ±10%

    @staticmethod
    def calculate(
        attacker: CombatUnit,
        defender: CombatUnit,
        skill_multiplier: float = 1.0,
        skill_atk_flat: float = 0,
    ) -> DamageResult:
        result = DamageResult()

        # 1. 基础攻击力 * 技能倍率 + 技能固定伤害
        result.raw_damage = attacker.atk * skill_multiplier + skill_atk_flat

        # 2. 防御减免：damage_reduction = DEF / (DEF + 100)
        def_factor = defender.defense / (defender.defense + 100)
        result.def_reduction = result.raw_damage * def_factor
        result.after_def = result.raw_damage - result.def_reduction

        # 3. 暴击判定
        if random.random() * 100 < attacker.crit_rate:
            result.is_crit = True
            result.crit_mult = attacker.crit_dmg / 100
        else:
            result.crit_mult = 1.0
        result.after_crit = result.after_def * result.crit_mult

        # 4. 元素克制
        result.element_mult = get_element_multiplier(attacker.element, defender.element)
        result.after_element = result.after_crit * result.element_mult

        # 5. 伤害浮动 ±10%
        result.variance = 1.0 + random.uniform(-DamageCalculator.DAMAGE_VARIANCE,
                                                DamageCalculator.DAMAGE_VARIANCE)
        result.final_damage = result.after_element * result.variance

        # 最小 1 伤害（如果原始伤害 > 0）
        result.final_damage = max(1, result.final_damage) if result.raw_damage > 0 else 0

        return result


# ─── 战斗模拟 ─────────────────────────────────────────────────────
class BattleSimulator:
    """回合制战斗模拟"""

    def __init__(self, team_a: list[CombatUnit], team_b: list[CombatUnit]):
        self.team_a = team_a
        self.team_b = team_b

    def _get_turn_order(self) -> list[CombatUnit]:
        """按速度降序排列行动顺序"""
        all_units = [u for u in self.team_a + self.team_b if u.is_alive]
        all_units.sort(key=lambda u: u.speed, reverse=True)
        return all_units

    def _find_target(self, attacker: CombatUnit) -> Optional[CombatUnit]:
        """找到攻击目标（敌方存活单位）"""
        enemy_team = self.team_b if attacker in self.team_a else self.team_a
        alive = [u for u in enemy_team if u.is_alive]
        return alive[0] if alive else None

    def simulate_round(self, round_num: int) -> bool:
        """模拟一回合，返回是否有存活双方"""
        print(f"\n{'='*50}")
        print(f"  第 {round_num} 回合")
        print(f"{'='*50}")

        turn_order = self._get_turn_order()
        if not turn_order:
            return False

        for unit in turn_order:
            if not unit.is_alive:
                continue

            target = self._find_target(unit)
            if target is None:
                return False  # 一方全灭

            # 攻击！
            print(f"\n⚡ {unit.name} 攻击 {target.name}")
            print(f"   元素: {unit.element.name} → {target.element.name}")

            damage = DamageCalculator.calculate(unit, target, skill_multiplier=1.0)
            damage.print()

            result_msg = target.take_damage(damage.final_damage)
            print(f"  {result_msg}")

            if not target.is_alive:
                print(f"  💀 {target.name} 已阵亡！")

        # 检查胜负
        team_a_alive = any(u.is_alive for u in self.team_a)
        team_b_alive = any(u.is_alive for u in self.team_b)
        if not team_a_alive:
            print(f"\n{'='*50}")
            print("  🏆 B 队获胜！")
            print(f"{'='*50}")
            return False
        if not team_b_alive:
            print(f"\n{'='*50}")
            print("  🏆 A 队获胜！")
            print(f"{'='*50}")
            return False
        return True


# ─── 演示 ────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  战斗系统演示 — 伤害公式完整链路")
    print("=" * 60)

    # 1. 单次伤害计算演示
    print("\n📊 1. 单次伤害计算演示")
    print("-" * 40)

    attacker = CombatUnit("烈焰剑士", atk=120, defense=40, crit_rate=25,
                          crit_dmg=180, element=Element.FIRE)
    defender = CombatUnit("草魔导师", atk=90, defense=60, crit_rate=15,
                          element=Element.GRASS)

    print(f"  攻击方: {attacker.name} (ATK={attacker.atk}, 元素={attacker.element.name})")
    print(f"  防御方: {defender.name} (DEF={defender.defense}, 元素={defender.element.name})")
    print(f"  元素克制: 火→草 = 1.5x")

    damage = DamageCalculator.calculate(attacker, defender, skill_multiplier=1.0)
    damage.print()

    # 2. 防御减免曲线
    print(f"\n📈 2. 防御减免曲线 (ATK=100)")
    print("-" * 50)
    print(f"{'DEF':>5s} | {'减免率':>7s} | {'最终伤害':>8s}")
    print("-" * 25)
    for def_val in [0, 25, 50, 100, 200, 400, 800]:
        reduction = def_val / (def_val + 100)
        after_def = 100 * (1 - reduction)
        print(f"{def_val:>5d} | {reduction*100:>6.1f}% | {after_def:>8.1f}")

    # 3. 小型战斗模拟
    print(f"\n⚔️  3. 回合制战斗模拟")
    print("-" * 40)

    team_a = [
        CombatUnit("🔥 火战士", atk=110, defense=45, hp=600, crit_rate=20,
                   crit_dmg=160, element=Element.FIRE, speed=110),
        CombatUnit("💧 水法师", atk=130, defense=30, hp=450, crit_rate=15,
                   element=Element.WATER, speed=95),
    ]
    team_b = [
        CombatUnit("🌿 草弓手", atk=100, defense=50, hp=550, crit_rate=25,
                   element=Element.GRASS, speed=105),
        CombatUnit("🌑 暗骑士", atk=95, defense=70, hp=700, crit_rate=10,
                   element=Element.DARK, speed=85),
    ]

    print("  队伍 A:")
    for u in team_a:
        print(f"    {u.name} HP={u.hp:.0f} ATK={u.atk} DEF={u.defense} SPD={u.speed}")
    print("  队伍 B:")
    for u in team_b:
        print(f"    {u.name} HP={u.hp:.0f} ATK={u.atk} DEF={u.defense} SPD={u.speed}")

    battle = BattleSimulator(team_a, team_b)
    for rnd in range(1, 21):
        if not battle.simulate_round(rnd):
            break
    else:
        print("\n⚠️  20回合未分胜负，平局！")

    print(f"\n✅ 战斗结束")


if __name__ == "__main__":
    main()
