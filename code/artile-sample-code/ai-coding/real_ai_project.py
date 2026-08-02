"""
AI 生成实战：从零做一个游戏背包系统

对应文章：AI Coding/用 AI Coding 从零做出游戏原型

演示用 AI 生成一个完整功能模块的完整提示词 + 产出代码。
"""

# ============================================================
# 步骤 1：提示词（这是给 AI 的输入）
# ============================================================
PROMPT = """
你是一位资深游戏开发工程师。请实现一个游戏背包系统，Python 3纯标准库。

需求：
1. 物品有：id、名称、类型(武器/防具/消耗品/材料)、稀有度(普通/稀有/史诗/传说)
2. 背包有格子数限制(默认20格)
3. 物品可堆叠(消耗品和材料最多99个)
4. 支持：添加物品、移除物品、使用物品、按类型/稀有度排序
5. 使用消耗品会减少数量，归零自动移除
6. 传说品质物品边框显示不同
7. 提供 main() 演示函数

输出完整可运行 Python 代码。
"""

# ============================================================
# 步骤 2：AI 生成的代码（质量取决于提示词质量）
# 以下是用上面提示词生成的代码：
# ============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class ItemType(Enum):
    WEAPON = "武器"
    ARMOR = "防具"
    CONSUMABLE = "消耗品"
    MATERIAL = "材料"


class Rarity(Enum):
    COMMON = ("普通", "⚪")
    RARE = ("稀有", "🔵")
    EPIC = ("史诗", "🟣")
    LEGENDARY = ("传说", "🟡")

    def __init__(self, label, icon):
        self._label = label
        self._icon = icon

    @property
    def label(self): return self._label
    @property
    def icon(self): return self._icon


@dataclass
class Item:
    id: str
    name: str
    item_type: ItemType
    rarity: Rarity = Rarity.COMMON
    stackable: bool = False
    max_stack: int = 1
    quantity: int = 1
    description: str = ""

    @property
    def is_stackable(self):
        return self.item_type in (ItemType.CONSUMABLE, ItemType.MATERIAL)


@dataclass
class InventorySlot:
    item: Item
    quantity: int = 1


class Inventory:
    def __init__(self, capacity: int = 20):
        self.capacity = capacity
        self.slots: List[Optional[InventorySlot]] = [None] * capacity

    def add_item(self, item: Item) -> bool:
        if item.is_stackable:
            for slot in self.slots:
                if slot and slot.item.id == item.id and slot.quantity < item.max_stack:
                    slot.quantity += item.quantity
                    print(f"  📦 堆叠 {item.name} (x{item.quantity}) → 当前 x{slot.quantity}")
                    return True

        for i, slot in enumerate(self.slots):
            if slot is None:
                self.slots[i] = InventorySlot(item, item.quantity)
                print(f"  ✅ 添加 {item.name} (x{item.quantity}) 到格子 {i+1}")
                return True

        print(f"  ❌ 背包已满！")
        return False

    def remove_item(self, slot_idx: int, quantity: int = 1) -> bool:
        if 0 <= slot_idx < self.capacity and self.slots[slot_idx]:
            slot = self.slots[slot_idx]
            slot.quantity -= quantity
            if slot.quantity <= 0:
                self.slots[slot_idx] = None
            return True
        return False

    def use_item(self, slot_idx: int) -> str:
        slot = self.slots[slot_idx]
        if not slot or slot.item.item_type != ItemType.CONSUMABLE:
            return "不可使用"
        effect = f"使用了 {slot.item.name}"
        self.remove_item(slot_idx, 1)
        return effect

    def sort_by_rarity(self):
        items = [(i, s) for i, s in enumerate(self.slots) if s]
        items.sort(key=lambda x: list(Rarity).index(x[1].item.rarity), reverse=True)
        new_slots = [None] * self.capacity
        for new_i, (_, slot) in enumerate(items):
            new_slots[new_i] = slot
        self.slots = new_slots

    def display(self):
        print(f"\n🎒 背包 ({sum(1 for s in self.slots if s)}/{self.capacity}):")
        print("-" * 55)
        for i, slot in enumerate(self.slots):
            if slot:
                item = slot.item
                icon = item.rarity.icon
                qty = f" x{slot.quantity}" if slot.quantity > 1 else ""
                print(f"  [{i+1:2d}] {icon} {item.name}{qty} ({item.item_type.value})")
            else:
                print(f"  [{i+1:2d}] — 空 —")
        print("-" * 55)


def main():
    print("=== AI 辅助编程演示：背包系统 ===\n")

    print("📝 步骤1：设计提示词")
    print(PROMPT[:200] + "...\n")

    print("🤖 步骤2：AI 生成代码（以下为生成结果演示）\n")

    inv = Inventory(10)

    # 添加物品
    items = [
        Item("sword_01", "铁剑", ItemType.WEAPON, Rarity.COMMON),
        Item("armor_01", "皮甲", ItemType.ARMOR, Rarity.RARE),
        Item("potion_hp", "生命药水", ItemType.CONSUMABLE, Rarity.COMMON,
             max_stack=99, quantity=5),
        Item("gem_fire", "火焰宝石", ItemType.MATERIAL, Rarity.EPIC,
             max_stack=99, quantity=3),
        Item("sword_legend", "圣剑·Excalibur", ItemType.WEAPON, Rarity.LEGENDARY),
    ]

    print("[添加物品]")
    for item in items:
        inv.add_item(item)

    inv.display()

    print("\n[使用生命药水]")
    print(f"  {inv.use_item(2)}")

    print("\n[按稀有度排序]")
    inv.sort_by_rarity()
    inv.display()

    print("\n✅ 背包系统演示完成")
    print("\n💡 提示：这是用 AI 生成的代码。关键在于提示词写清需求+约束+输出格式。")


if __name__ == "__main__":
    main()
