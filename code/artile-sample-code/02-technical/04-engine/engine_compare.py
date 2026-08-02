#!/usr/bin/env python3
"""
游戏引擎选型对比 — Unity vs Godot vs Cocos + 决策树

纯标准库实现，提供：
1. 多维度特性对比表
2. 交互式选型决策树
3. 场景推荐评分

运行：python engine_compare.py
"""

import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# ──────────────────────────────────────────────
# 引擎数据模型
# ──────────────────────────────────────────────


@dataclass
class EngineInfo:
    """引擎信息"""
    name: str
    version: str
    developer: str
    license_type: str
    platforms: List[str]
    languages: List[str]
    render_pipelines: List[str]
    strengths: List[str]
    weaknesses: List[str]
    pricing: str
    community_size: str
    learning_curve: str  # easy / medium / hard
    best_for: List[str]
    scores: Dict[str, float] = field(default_factory=dict)


# 引擎数据
ENGINES = {
    "Unity": EngineInfo(
        name="Unity",
        version="Unity 6 (2024+)",
        developer="Unity Technologies",
        license_type="个人免费 / 商业付费",
        platforms=["Windows", "macOS", "Linux", "iOS", "Android", "WebGL", "Switch", "PS5", "Xbox"],
        languages=["C#"],
        render_pipelines=["URP", "HDRP", "Built-in"],
        strengths=[
            "最大的社区和 Asset Store 生态",
            "跨平台能力最强",
            "丰富的学习资源和教程",
            "C# 易于上手",
        ],
        weaknesses=[
            "引擎体积庞大，编译慢",
            "闭源，遇到引擎 bug 难以自行修复",
            "授权费用争议 (Runtime Fee)",
            "2D 工具链不如专用引擎",
        ],
        pricing="个人免费 (年收入 <$200K)，Pro $2,040/年/席",
        community_size="非常庞大 (全球 #1)",
        learning_curve="medium",
        best_for=["3D 手游", "跨平台独立游戏", "AR/VR", "多人网游"],
    ),
    "Godot": EngineInfo(
        name="Godot",
        version="Godot 4.x",
        developer="Godot Foundation (社区驱动)",
        license_type="MIT 开源 (完全免费)",
        platforms=["Windows", "macOS", "Linux", "iOS", "Android", "WebGL", "Switch(社区)"],
        languages=["GDScript", "C#", "C++ (GDExtension)"],
        render_pipelines=["Forward+", "Mobile", "Compatibility"],
        strengths=[
            "完全开源，MIT 协议无任何费用",
            "轻量级 (~50MB)，启动快",
            "场景-节点架构直观",
            "原生 2D 渲染器 (像素完美)",
        ],
        weaknesses=[
            "3D 性能不如 Unity/Unreal",
            "社区和资源相对较小",
            "主机平台支持有限",
            "GDScript 性能不如 C#/C++",
        ],
        pricing="完全免费，无任何限制",
        community_size="快速增长中 (第二梯队)",
        learning_curve="easy",
        best_for=["2D 游戏", "独立游戏", "原型快速开发", "开源项目"],
    ),
    "Cocos": EngineInfo(
        name="Cocos Creator",
        version="Cocos Creator 3.x",
        developer="Cocos (触控科技)",
        license_type="开源免费 (MIT)",
        platforms=["iOS", "Android", "Web", "小游戏平台 (微信/抖音等)", "Windows", "macOS"],
        languages=["TypeScript", "JavaScript"],
        render_pipelines=["Forward Rendering", "Deferred (3.x)"],
        strengths=[
            "微信小游戏 / 抖音小游戏首选",
            "轻量级，H5 性能优秀",
            "中国市场生态完善",
            "TypeScript 对前端开发者友好",
        ],
        weaknesses=[
            "国际市场占有率低",
            "3D 能力较弱",
            "社区以中文为主",
            "编辑器稳定性有提升空间",
        ],
        pricing="免费 (企业定制服务收费)",
        community_size="中等 (中国最大)",
        learning_curve="easy",
        best_for=["H5 游戏", "微信小游戏", "休闲手游", "2D 卡牌/RPG"],
    ),
    "Unreal": EngineInfo(
        name="Unreal Engine 5",
        version="UE 5.x",
        developer="Epic Games",
        license_type="免费 (收入超 $1M 后 5% 分成)",
        platforms=["Windows", "macOS", "Linux", "iOS", "Android", "Switch", "PS5", "Xbox"],
        languages=["C++", "Blueprint (可视化)"],
        render_pipelines=["Lumen", "Nanite", "Path Tracer"],
        strengths=[
            "业界顶级画面质量 (Nanite/Lumen)",
            "蓝图可视化脚本降低门槛",
            "AAA 级别工具链完整",
            "Epic 游戏生态 (Megascans 等)",
        ],
        weaknesses=[
            "学习曲线陡峭",
            "硬件要求高 (开发机 + 目标设备)",
            "C++ 编译速度慢",
            "移动端包体大，性能开销高",
        ],
        pricing="免费 (<$1M 收入)，超出后 5%",
        community_size="非常大",
        learning_curve="hard",
        best_for=["AAA 游戏", "高端 3D", "影视/建筑可视化", "PC/主机大作"],
    ),
}


# ──────────────────────────────────────────────
# 显示工具
# ──────────────────────────────────────────────


def print_table(headers: List[str], rows: List[List[str]], col_widths: List[int] = None):
    """打印格式化表格"""
    if col_widths is None:
        col_widths = [max(len(str(r[i])) for r in [headers] + rows) + 2 for i in range(len(headers))]

    def row_str(row):
        return "│" + "│".join(f" {str(c).ljust(col_widths[i] - 1)}" for i, c in enumerate(row)) + "│"

    sep = "├" + "┼".join("─" * w for w in col_widths) + "┤"
    top = "┌" + "┬".join("─" * w for w in col_widths) + "┐"
    bot = "└" + "┴".join("─" * w for w in col_widths) + "┘"

    print(top)
    print(row_str(headers))
    print(sep)
    for row in rows:
        print(row_str(row))
    print(bot)


def print_comparison():
    """打印引擎对比表"""
    print()
    print("═" * 70)
    print("  游戏引擎多维度对比")
    print("═" * 70)

    headers = ["维度", "Unity", "Godot", "Cocos Creator", "Unreal Engine 5"]
    rows = [
        ["许可证", "个人免费/商业付费", "MIT 开源 (完全免费)", "MIT 开源", "免费 (<$1M)/5%分成"],
        ["主要语言", "C#", "GDScript / C# / C++", "TypeScript", "C++ / Blueprint"],
        ["编辑器体积", "~5GB+", "~50MB", "~500MB", "~30GB+"],
        ["2D 支持", "中等 (Tilemap等)", "★★★★★ 顶级", "★★★★☆ 优秀", "较弱"],
        ["3D 支持", "★★★★★", "★★★☆☆", "★★☆☆☆", "★★★★★ 顶级"],
        ["小游戏/H5", "一般", "一般", "★★★★★ 首选", "不支持"],
        ["AR/VR", "★★★★★", "★★☆☆☆", "★☆☆☆☆", "★★★★★"],
        ["学习难度", "中等", "简单", "简单", "困难"],
        ["社区规模", "全球最大", "快速增长", "中国最大", "非常大"],
        ["主机支持", "完整", "有限(社区)", "不支持", "完整"],
    ]

    print_table(headers, rows)
    print()


def print_scores():
    """打印场景评分"""
    print("═" * 70)
    print("  场景适配评分 (★★★★★ 满分)")
    print("═" * 70)

    headers = ["使用场景", "Unity", "Godot", "Cocos", "Unreal"]
    scenarios = [
        ("2D 独立游戏",         "★★★☆☆", "★★★★★", "★★★★☆", "★★☆☆☆"),
        ("2D 手机休闲",          "★★★★☆", "★★★★☆", "★★★★★", "★☆☆☆☆"),
        ("微信小游戏",           "★★☆☆☆", "★★☆☆☆", "★★★★★", "☆☆☆☆☆"),
        ("3D 手游 (中高质量)",    "★★★★★", "★★★☆☆", "★★☆☆☆", "★★★★☆"),
        ("3D AAA / PC大作",      "★★★★☆", "★★☆☆☆", "★☆☆☆☆", "★★★★★"),
        ("AR/VR 应用",           "★★★★★", "★★☆☆☆", "★☆☆☆☆", "★★★★★"),
        ("H5 网页游戏",          "★★★☆☆", "★★★★☆", "★★★★★", "★☆☆☆☆"),
        ("快速原型",             "★★★★☆", "★★★★★", "★★★★☆", "★★☆☆☆"),
        ("团队: 前端背景",       "★★★☆☆", "★★★★☆", "★★★★★", "★★☆☆☆"),
        ("团队: C# 背景",        "★★★★★", "★★★★☆", "★★☆☆☆", "★★☆☆☆"),
        ("团队: C++ 背景",       "★★★★☆", "★★★☆☆", "★☆☆☆☆", "★★★★★"),
        ("零预算项目",           "★★★☆☆", "★★★★★", "★★★★★", "★★★★☆"),
    ]

    print_table(headers, scenarios)
    print()


# ──────────────────────────────────────────────
# 交互式决策树
# ──────────────────────────────────────────────


class DecisionNode:
    """决策树节点"""
    def __init__(self, question: str, choices: Dict[str, "DecisionNode"] = None, result: str = None):
        self.question = question
        self.choices = choices or {}
        self.result = result

    def is_leaf(self):
        return self.result is not None


def build_decision_tree() -> DecisionNode:
    """构建选型决策树"""
    # 叶子节点
    unity = DecisionNode("", result="Unity")
    godot = DecisionNode("", result="Godot")
    cocos = DecisionNode("", result="Cocos Creator")
    unreal = DecisionNode("", result="Unreal Engine 5")
    unity_or_unreal = DecisionNode("", result="Unity / Unreal Engine 5")
    godot_or_unity = DecisionNode("", result="Godot / Unity")

    # 第二层
    q_target = DecisionNode("你的主要目标平台是？", {
        "1": DecisionNode("", result="PC / 主机", choices={
            "1": unreal,
            "2": unity,
        }),
        "2": DecisionNode("", result="移动端 (iOS/Android)", choices={
            "1": DecisionNode("需要顶级画面？", {"1": unreal, "2": unity_or_unreal}),
        }),
        "3": DecisionNode("", result="H5 网页 / 小游戏", choices={
            "1": cocos,
            "2": DecisionNode("主要 2D？", {"1": godot, "2": cocos}),
        }),
    })

    # 第一层 (根)
    root = DecisionNode("你要做什么类型的游戏？", {
        "1": DecisionNode("2D 游戏", question="", choices={
            "1": DecisionNode("需要发布小游戏平台？", {"1": cocos, "2": godot}),
        }),
        "2": DecisionNode("3D 游戏", question="", choices={
            "1": q_target,
        }),
        "3": DecisionNode("AR/VR 应用", question="", choices={
            "1": unity,
        }),
    })

    return root


def run_decision_tree():
    """运行交互式决策树"""
    print("═" * 70)
    print("  游戏引擎选型决策树")
    print("═" * 70)
    print()
    print("  回答以下问题，系统将推荐适合你的游戏引擎：")
    print()

    tree = {
        "question": "你要做什么类型的游戏？",
        "options": [
            ("1", "2D 游戏"),
            ("2", "3D 游戏"),
            ("3", "AR/VR 应用"),
        ],
        "1": {
            "question": "是否需要发布到微信/抖音小游戏平台？",
            "options": [
                ("1", "是，必须支持小游戏"),
                ("2", "不需要或无所谓"),
            ],
            "1": {"result": "Cocos Creator", "reason": "小游戏平台首选引擎，TypeScript 生态完善"},
            "2": {"result": "Godot", "reason": "2D 渲染器顶级，MIT 开源免费，轻量级"},
        },
        "2": {
            "question": "你的主要目标平台是？",
            "options": [
                ("1", "PC / 主机"),
                ("2", "移动端 (iOS/Android)"),
                ("3", "H5 网页"),
            ],
            "1": {
                "question": "目标是 AAA 级画质还是独立游戏？",
                "options": [
                    ("1", "AAA 级画质 / 影视级"),
                    ("2", "独立游戏 / 中等画质即可"),
                ],
                "1": {"result": "Unreal Engine 5", "reason": "Nanite/Lumen 技术业界领先，AAA 标配"},
                "2": {"result": "Unity", "reason": "灵活性和跨平台最佳平衡，生态最大"},
            },
            "2": {
                "question": "对画面质量的要求是？",
                "options": [
                    ("1", "追求顶级移动端画质"),
                    ("2", "中等即可，更看重性能"),
                ],
                "1": {"result": "Unreal Engine 5", "reason": "移动端渲染优化在快速提升"},
                "2": {"result": "Unity", "reason": "移动端市场占有率最高，优化成熟"},
            },
            "3": {"result": "Cocos Creator", "reason": "H5 性能最优，小游戏生态第一"},
        },
        "3": {"result": "Unity", "reason": "AR/VR 支持最完善，Asset Store 生态丰富"},
    }

    def traverse(node, depth=0):
        if "result" in node:
            indent = "  " * depth
            print(f"{indent}🎯 推荐引擎: {node['result']}")
            print(f"{indent}   理由: {node.get('reason', '综合评分最高')}")
            return

        print(f"\n{'  ' * depth}❓ {node['question']}")
        for key, label in node.get("options", []):
            print(f"{'  ' * depth}  [{key}] {label}")

        while True:
            choice = input(f"{'  ' * depth}👉 请输入选项 (或 q 退出): ").strip()
            if choice.lower() == "q":
                print("  退出决策树。")
                return
            if choice in node:
                traverse(node[choice], depth + 1)
                return
            opts = [o[0] for o in node.get("options", [])]
            print(f"  无效选项，请输入 {opts}")

    traverse(tree)


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────


def main():
    print("=" * 70)
    print("  游戏引擎选型对比工具")
    print("  Unity vs Godot vs Cocos Creator vs Unreal Engine 5")
    print("=" * 70)

    # 1. 特性对比表
    print_comparison()

    # 2. 场景评分
    print_scores()

    # 3. 决策树
    print("\n" + "═" * 70)
    print("  是否使用交互式决策树？")
    print("═" * 70)
    choice = input("  输入 y 开始选型，其他键跳过: ").strip().lower()

    if choice == "y":
        run_decision_tree()

    print()
    print("=" * 70)
    print("  提示: 实际选型还需考虑团队技能栈、项目周期、预算等因素。")
    print("  本工具仅从技术维度提供参考。")
    print("=" * 70)


if __name__ == "__main__":
    main()
