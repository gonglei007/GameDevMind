#!/usr/bin/env python3
"""
角色属性系统演示：基础属性 → 装备加成 → Buff 修改器链 → 最终值
纯标准库，直接运行。

属性计算链：
  BASE 基础值
  → + EQUIP 装备固定加成
  → + EQUIP 装备百分比加成  
  → * BUFF 百分比修改器
  → + BUFF 固定修改器
  → * 衰减/上限钳制
  = FINAL 最终值
"""

from dataclasses import dataclass, field
from typing import Callable


# ─── 修改器 ──────────────────────────────────────────────────────
@dataclass
class Modifier:
    """属性修改器"""
    name: str
    priority: int  # 越低越先应用
    apply: Callable[[float], float]
    source: str = ""  # 来源（装备/Buff/被动）
    duration: float = -1  # -1 表示永久

    def __repr__(self):
        return f"Modifier({self.name}, pri={self.priority})"


# ─── 属性定义 ────────────────────────────────────────────────────
@dataclass
class Attribute:
    """单个属性：持有基础值 + 修改器链"""
    name: str
    base: float = 0.0
    modifiers: list[Modifier] = field(default_factory=list)
    min_value: float = 0.0
    max_value: float = float("inf")

    def add_modifier(self, mod: Modifier):
        self.modifiers.append(mod)
        self.modifiers.sort(key=lambda m: m.priority)

    def remove_modifier(self, name: str):
        self.modifiers = [m for m in self.modifiers if m.name != name]

    def get_final(self) -> float:
        """遍历修改器链计算最终值"""
        value = self.base
        for mod in self.modifiers:
            value = mod.apply(value)
        # 钳制
        value = max(self.min_value, min(self.max_value, value))
        return value

    def get_breakdown(self) -> list[tuple[str, float]]:
        """返回计算明细"""
        steps = [("BASE", self.base)]
        value = self.base
        for mod in self.modifiers:
            new_value = mod.apply(value)
            steps.append((f"  {mod.name} ({mod.source})", new_value - value))
            value = new_value
        value = max(self.min_value, min(self.max_value, value))
        steps.append(("= FINAL", value))
        return steps


# ─── 角色属性集 ──────────────────────────────────────────────────
class CharacterAttributes:
    """角色完整属性面板"""

    def __init__(self, name: str):
        self.name = name
        self.attrs: dict[str, Attribute] = {
            "ATK":   Attribute("攻击力", base=100, min_value=0),
            "DEF":   Attribute("防御力", base=50, min_value=0),
            "HP":    Attribute("生命值", base=1000, min_value=1),
            "SPD":   Attribute("速度", base=100, min_value=10, max_value=500),
            "CRIT":  Attribute("暴击率(%)", base=5, min_value=0, max_value=100),
            "CDMG":  Attribute("暴击伤害(%)", base=150, min_value=100),
        }

    def equip(self, item_name: str, attr_name: str, flat: float = 0, pct: float = 0):
        """装备属性加成"""
        if attr_name not in self.attrs:
            return
        if flat:
            self.attrs[attr_name].add_modifier(Modifier(
                f"{item_name}+flat", priority=10,
                apply=lambda v, f=flat: v + f,
                source=item_name,
            ))
        if pct:
            self.attrs[attr_name].add_modifier(Modifier(
                f"{item_name}+%", priority=20,
                apply=lambda v, p=pct: v * (1 + p / 100),
                source=item_name,
            ))

    def buff(self, buff_name: str, attr_name: str,
             pct: float = 0, flat: float = 0, duration: float = 10):
        """Buff 修改器"""
        if attr_name not in self.attrs:
            return
        if pct:
            self.attrs[attr_name].add_modifier(Modifier(
                f"{buff_name}%", priority=30,
                apply=lambda v, p=pct: v * (1 + p / 100),
                source=buff_name,
                duration=duration,
            ))
        if flat:
            self.attrs[attr_name].add_modifier(Modifier(
                f"{buff_name}+flat", priority=40,
                apply=lambda v, f=flat: v + f,
                source=buff_name,
                duration=duration,
            ))

    def remove_buff(self, buff_name: str):
        """移除指定 Buff"""
        for attr in self.attrs.values():
            attr.remove_modifier(buff_name + "%")
            attr.remove_modifier(buff_name + "+flat")

    def get_sheet(self) -> dict[str, float]:
        """获取所有最终属性"""
        return {name: attr.get_final() for name, attr in self.attrs.items()}

    def print_sheet(self):
        """打印属性面板"""
        print(f"\n{'='*50}")
        print(f"  {self.name} 属性面板")
        print(f"{'='*50}")
        print(f"{'属性':>12s} | {'最终值':>10s} | 计算明细")
        print("-" * 50)
        for name, attr in self.attrs.items():
            final = attr.get_final()
            safe = attr.name if attr.name else name
            print(f"{safe:>12s} | {final:>10.1f} | ", end="")
            steps = attr.get_breakdown()
            detail = " → ".join(f"{s[0]}({s[1]:+.0f})" for s in steps[1:-1])
            print(detail)
        print("=" * 50)


# ─── 演示 ────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  角色属性系统演示 — 修改器链计算")
    print("=" * 60)

    char = CharacterAttributes("战士")

    # 1. 基础属性
    print("\n📋 1. 基础属性（无装备）")
    char.print_sheet()

    # 2. 装备
    print("\n🗡️  2. 装备「龙鳞甲」：DEF+80, HP+300")
    char.equip("龙鳞甲", "DEF", flat=80)
    char.equip("龙鳞甲", "HP", flat=300)
    char.print_sheet()

    print("\n⚔️  3. 装备「烈焰剑」：ATK+50, ATK+15%")
    char.equip("烈焰剑", "ATK", flat=50, pct=15)
    char.print_sheet()

    # 3. Buff
    print("\n✨ 4. 获得 Buff「战吼」：ATK+30%, SPD+20%")
    char.buff("战吼", "ATK", pct=30)
    char.buff("战吼", "SPD", pct=20)
    char.print_sheet()

    print("\n🛡️  5. 获得 Buff「铁壁」：DEF+25%")
    char.buff("铁壁", "DEF", pct=25)
    char.print_sheet()

    # 4. 计算明细
    print("\n📊 6. ATK 完整计算链：")
    for step_name, delta in char.attrs["ATK"].get_breakdown():
        marker = "◀" if step_name.startswith("=") else "  "
        print(f"   {marker} {step_name:<30s} {delta:>+10.1f}")

    # 5. 移除 Buff
    print("\n💨 7. 战吼效果结束")
    char.remove_buff("战吼")
    char.print_sheet()

    print(f"\n✅ 最终属性: {char.get_sheet()}")


if __name__ == "__main__":
    main()
