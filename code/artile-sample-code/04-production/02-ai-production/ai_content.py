#!/usr/bin/env python3
"""
AI辅助内容生成：物品名/描述批量生成（模板+规则引擎）
纯标准库，直接运行。

工作流：
  1. 物品模板定义（稀有度、类别、词缀）
  2. 基于规则的名称生成（前缀+核心+后缀）
  3. 描述生成（模板填充 + 参数插值）
  4. 批量生成与质量评分
  5. 平衡性检查（属性总和约束）
"""
import random
import json
import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── 定义 ──────────────────────────────────────────────────────────
class Rarity(Enum):
    COMMON = ("普通", 1.0, "⚪")
    UNCOMMON = ("精良", 1.3, "🟢")
    RARE = ("稀有", 1.6, "🔵")
    EPIC = ("史诗", 2.0, "🟣")
    LEGENDARY = ("传说", 2.5, "🟡")

    def __init__(self, label: str, multiplier: float, icon: str):
        self.label = label
        self.multiplier = multiplier
        self.icon = icon


class ItemCategory(Enum):
    WEAPON = "武器"
    ARMOR = "防具"
    ACCESSORY = "饰品"
    CONSUMABLE = "消耗品"
    MATERIAL = "材料"


class ElementAffix(Enum):
    NONE = ("无", 0)
    FIRE = ("烈焰", 15)
    ICE = ("寒冰", 15)
    THUNDER = ("雷霆", 15)
    POISON = ("毒素", 12)
    LIGHT = ("圣光", 18)
    SHADOW = ("暗影", 18)

    def __init__(self, label: str, bonus: int):
        self.label = label
        self.bonus = bonus


@dataclass
class ItemTemplate:
    """物品生成模板"""
    category: ItemCategory
    rarity: Rarity
    base_name: str
    min_level: int = 1
    base_attack: int = 0
    base_defense: int = 0
    base_hp: int = 0
    prefix_pool: list = field(default_factory=list)
    suffix_pool: list = field(default_factory=list)


@dataclass
class GeneratedItem:
    """生成的物品"""
    name: str
    category: ItemCategory
    rarity: Rarity
    level: int
    attack: int
    defense: int
    hp: int
    element: ElementAffix = ElementAffix.NONE
    description: str = ""
    flavor_text: str = ""
    quality_score: float = 0.0


# ─── 模板库 ────────────────────────────────────────────────────────
PREFIX_POOL = {
    "通用正面": ["坚韧的", "锋利的", "坚固的", "迅捷的", "精密的", "华丽的"],
    "通用负面": ["锈蚀的", "残破的", "笨重的", "暗淡的", "磨损的"],
    "元素": ["灼热的", "冰霜的", "雷电的", "剧毒的", "圣光的", "暗影的"],
    "史诗": ["龙息", "不朽", "无尽", "破晓", "黄昏", "混沌", "永恒", "虚空"],
}

SUFFIX_POOL = {
    "武器": ["之刃", "之矛", "之弓", "之杖", "之斧", "之锤", "之剑"],
    "防具": ["之铠", "之盾", "之盔", "之靴", "之甲", "之袍"],
    "饰品": ["之戒", "之链", "之环", "之印", "之珠"],
    "通用": ["毁灭者", "守护者", "征服者", "先知", "旅者", "贤者"],
}

FLAVOR_TEXTS = {
    Rarity.COMMON: [
        "一把普通的{category}，没什么特别的。",
        "随处可见的{category}。",
    ],
    Rarity.UNCOMMON: [
        "做工精良的{category}，值得信赖。",
        "比起一般的{category}，这件显然更用心。",
    ],
    Rarity.RARE: [
        "稀有{category}，锻造时融入了{material}。",
        "这件{category}散发着微弱的光芒——它不是凡品。",
    ],
    Rarity.EPIC: [
        "传说{hero}曾用这件{category}斩杀了{boss}。",
        "即便是王国最优秀的铁匠，终其一生也难锻造出第二件。",
    ],
    Rarity.LEGENDARY: [
        "创世之初便存在的{category}，它的故事已经失传。",
        "没有人知道这件{category}的真正力量——因为见过的人都没能活下来。",
    ],
}

ITEM_TEMPLATES = [
    ItemTemplate(ItemCategory.WEAPON, Rarity.COMMON, "短剑",
                 base_attack=5, prefix_pool=PREFIX_POOL["通用正面"][:2],
                 suffix_pool=SUFFIX_POOL["武器"]),
    ItemTemplate(ItemCategory.WEAPON, Rarity.RARE, "长剑",
                 base_attack=25, prefix_pool=PREFIX_POOL["元素"],
                 suffix_pool=SUFFIX_POOL["武器"]),
    ItemTemplate(ItemCategory.WEAPON, Rarity.LEGENDARY, "巨剑",
                 base_attack=80, prefix_pool=PREFIX_POOL["史诗"],
                 suffix_pool=SUFFIX_POOL["武器"] + SUFFIX_POOL["通用"]),
    ItemTemplate(ItemCategory.ARMOR, Rarity.COMMON, "皮甲",
                 base_defense=5, base_hp=20,
                 prefix_pool=PREFIX_POOL["通用正面"][2:4],
                 suffix_pool=SUFFIX_POOL["防具"]),
    ItemTemplate(ItemCategory.ARMOR, Rarity.EPIC, "板甲",
                 base_defense=60, base_hp=150,
                 prefix_pool=PREFIX_POOL["史诗"],
                 suffix_pool=SUFFIX_POOL["防具"] + SUFFIX_POOL["通用"]),
    ItemTemplate(ItemCategory.ACCESSORY, Rarity.UNCOMMON, "戒指",
                 base_attack=3, base_defense=3, base_hp=30,
                 prefix_pool=PREFIX_POOL["元素"],
                 suffix_pool=SUFFIX_POOL["饰品"]),
    ItemTemplate(ItemCategory.ACCESSORY, Rarity.EPIC, "项链",
                 base_attack=20, base_defense=20, base_hp=120,
                 prefix_pool=PREFIX_POOL["史诗"],
                 suffix_pool=SUFFIX_POOL["饰品"]),
    ItemTemplate(ItemCategory.CONSUMABLE, Rarity.COMMON, "药水",
                 base_hp=50, prefix_pool=["小型", "微型"],
                 suffix_pool=["生命药剂", "治疗药剂"]),
]


def random_element_for_rarity(rarity: Rarity) -> ElementAffix:
    """根据稀有度随机元素（高稀有度更可能有元素）"""
    chance = {Rarity.COMMON: 0.0, Rarity.UNCOMMON: 0.1,
              Rarity.RARE: 0.3, Rarity.EPIC: 0.6, Rarity.LEGENDARY: 0.9}
    if random.random() < chance.get(rarity, 0.0):
        return random.choice([e for e in ElementAffix if e != ElementAffix.NONE])
    return ElementAffix.NONE


def generate_name(template: ItemTemplate, element: ElementAffix) -> str:
    """基于模板 + 前缀/后缀 + 元素 生成物品名称"""
    prefix = random.choice(template.prefix_pool) if template.prefix_pool else ""
    suffix = random.choice(template.suffix_pool) if template.suffix_pool else ""
    core = template.base_name

    # 元素词缀可以替换前缀
    if element != ElementAffix.NONE and random.random() < 0.5:
        prefix = element.label

    parts = [p for p in [prefix, core, suffix] if p]
    return "".join(parts)


def generate_description(item: GeneratedItem, template: ItemTemplate) -> str:
    """生成物品描述文字"""
    rarity_label = item.rarity.label
    cat_label = item.category.value

    stat_parts = []
    if item.attack > 0:
        stat_parts.append(f"攻击力+{item.attack}")
    if item.defense > 0:
        stat_parts.append(f"防御力+{item.defense}")
    if item.hp > 0:
        stat_parts.append(f"生命值+{item.hp}")
    if item.element != ElementAffix.NONE:
        stat_parts.append(f"{item.element.label}属性")

    desc = f"[{rarity_label}] {cat_label} · Lv{item.level}\n"
    desc += f"  {' | '.join(stat_parts)}"

    # 风味文字
    flavor_templates = FLAVOR_TEXTS.get(item.rarity, FLAVOR_TEXTS[Rarity.COMMON])
    flavor = random.choice(flavor_templates).format(
        category=cat_label,
        material=random.choice(["秘银", "龙鳞", "暗钢", "星陨铁"]),
        hero=random.choice(["亚瑟", "吉尔伽美什", "齐格飞", "贝奥武夫"]),
        boss=random.choice(["恶龙法芙纳", "魔君索伦", "巫妖王", "泰坦"]),
    )
    desc += f"\n  「{flavor}」"
    return desc


def generate_item(template: ItemTemplate, level: int = None) -> GeneratedItem:
    """从模板生成一件物品"""
    if level is None:
        level = random.randint(template.min_level, max(template.min_level, 60))

    element = random_element_for_rarity(template.rarity)
    name = generate_name(template, element)

    mult = template.rarity.multiplier
    level_factor = 1 + (level - 1) * 0.05

    item = GeneratedItem(
        name=name,
        category=template.category,
        rarity=template.rarity,
        level=level,
        attack=int(template.base_attack * mult * level_factor),
        defense=int(template.base_defense * mult * level_factor),
        hp=int(template.base_hp * mult * level_factor),
        element=element,
    )
    item.description = generate_description(item, template)
    item.quality_score = calculate_quality(item)
    return item


def calculate_quality(item: GeneratedItem) -> float:
    """质量评分：综合属性值 / 等级（带元素加成）"""
    total_stats = item.attack + item.defense + item.hp
    if item.level == 0:
        return 0.0
    base_score = total_stats / max(item.level, 1)
    element_bonus = item.element.bonus * 0.05 if item.element != ElementAffix.NONE else 0
    return round(base_score + element_bonus, 2)


def batch_generate(count: int = 20,
                   categories: list[ItemCategory] = None) -> list[GeneratedItem]:
    """批量生成物品，按稀有度分布"""
    templates = ITEM_TEMPLATES
    if categories:
        templates = [t for t in templates if t.category in categories]

    # 稀有度分布：越稀有越少
    rarity_weights = {
        Rarity.COMMON: 40, Rarity.UNCOMMON: 25,
        Rarity.RARE: 18, Rarity.EPIC: 12, Rarity.LEGENDARY: 5,
    }

    items = []
    for _ in range(count):
        rarity = random.choices(
            list(rarity_weights.keys()),
            weights=list(rarity_weights.values()), k=1
        )[0]
        matching = [t for t in templates if t.rarity == rarity]
        if not matching:
            matching = templates
        template = random.choice(matching)
        items.append(generate_item(template))

    return sorted(items, key=lambda i: i.quality_score, reverse=True)


def balance_check(items: list[GeneratedItem]) -> dict:
    """平衡性检查：统计属性分布"""
    stats = {
        "total_items": len(items),
        "by_rarity": {},
        "by_category": {},
        "avg_attack": 0.0, "avg_defense": 0.0, "avg_hp": 0.0,
        "avg_quality": 0.0,
        "element_distribution": {},
    }

    for item in items:
        r = item.rarity.label
        c = item.category.value
        stats["by_rarity"][r] = stats["by_rarity"].get(r, 0) + 1
        stats["by_category"][c] = stats["by_category"].get(c, 0) + 1
        stats["avg_attack"] += item.attack
        stats["avg_defense"] += item.defense
        stats["avg_hp"] += item.hp
        stats["avg_quality"] += item.quality_score
        stats["element_distribution"][item.element.label] = \
            stats["element_distribution"].get(item.element.label, 0) + 1

    n = max(len(items), 1)
    stats["avg_attack"] = round(stats["avg_attack"] / n, 1)
    stats["avg_defense"] = round(stats["avg_defense"] / n, 1)
    stats["avg_hp"] = round(stats["avg_hp"] / n, 1)
    stats["avg_quality"] = round(stats["avg_quality"] / n, 2)

    return stats


def export_to_json(items: list[GeneratedItem], path: str):
    """导出物品为 JSON（供游戏引擎读取）"""
    data = []
    for item in items:
        data.append({
            "name": item.name,
            "category": item.category.value,
            "rarity": item.rarity.name,
            "level": item.level,
            "attack": item.attack,
            "defense": item.defense,
            "hp": item.hp,
            "element": item.element.name,
            "description": item.description,
            "quality_score": item.quality_score,
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


# ─── 入口 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI辅助内容生成 · 物品批量生成器")
    print("=" * 60)

    # 批量生成 25 件物品
    items = batch_generate(25)
    balance = balance_check(items)

    print(f"\n📊 稀有度分布: {balance['by_rarity']}")
    print(f"📁 类别分布:   {balance['by_category']}")
    print(f"⚔ 平均攻击: {balance['avg_attack']} | 🛡 防御: {balance['avg_defense']} | ❤ HP: {balance['avg_hp']}")
    print(f"⭐ 平均质量: {balance['avg_quality']}")
    print(f"🔮 元素分布: {balance['element_distribution']}")

    print(f"\n── 生成物品 (Top 10) ──")
    for i, item in enumerate(items[:10], 1):
        icon = item.rarity.icon
        elem_tag = f" [{item.element.label}]" if item.element != ElementAffix.NONE else ""
        print(f"  {i:2d}. {icon} {item.name}{elem_tag} (Lv{item.level}) 品质:{item.quality_score}")
        print(f"      ⚔{item.attack} 🛡{item.defense} ❤{item.hp}")
        print(f"      {item.description.split(chr(10))[0]}")

    # 导出演示
    export_path = "./_ai_items_demo.json"
    export_to_json(items[:10], export_path)
    print(f"\n📄 已导出前10件至: {export_path}")

    # 模板扩展演示
    print(f"\n🧩 模板扩展示例 (自定义稀有武器):")
    custom_template = ItemTemplate(
        ItemCategory.WEAPON, Rarity.LEGENDARY, "圣剑",
        base_attack=100, min_level=50,
        prefix_pool=["断罪", "天罚", "救赎"],
        suffix_pool=["·誓约胜利之剑", "·诸神黄昏"],
    )
    custom_item = generate_item(custom_template, level=80)
    print(f"  {custom_item.name}")
    print(f"  {custom_item.description}")

    # 清理
    import os
    if os.path.exists(export_path):
        os.remove(export_path)
    print(f"\n🧹 已清理临时文件")
