"""
AI 对社会财富影响的简单模拟

对应文章：AI与社会财富的宏观思考
"""

import random


def simulate(population: int, ai_productivity_boost: float, years: int):
    """简单模拟 AI 提升生产率对财富分配的影响"""
    # 初始：每人财富随机
    wealth = [random.uniform(50, 150) for _ in range(population)]

    history = []
    for year in range(years):
        # AI 提升整体生产率
        growth = 1.03 + ai_productivity_boost * 0.05

        for i in range(population):
            # 不同人群受益不同：高财富者更能利用AI
            ai_multiplier = 1.0 + ai_productivity_boost * (wealth[i] / 200)
            wealth[i] *= growth * ai_multiplier * random.uniform(0.95, 1.05)

        # 计算基尼系数
        sorted_w = sorted(wealth)
        n = population
        gini = (2 * sum((i + 1) * w for i, w in enumerate(sorted_w))
                - (n + 1) * sum(sorted_w)) / (n * sum(sorted_w))

        history.append({
            "year": year + 1,
            "total": sum(wealth),
            "avg": sum(wealth) / n,
            "top10_share": sum(sorted_w[-n//10:]) / sum(wealth),
            "bottom50_share": sum(sorted_w[:n//2]) / sum(wealth),
            "gini": gini
        })

    return history


def main():
    print("=== AI 对社会财富影响的简单模拟 ===\n")

    scenarios = [
        ("无 AI", 0.0),
        ("温和 AI", 0.5),
        ("激进 AI", 1.5),
    ]

    for name, boost in scenarios:
        print(f"\n📊 场景: {name} (AI生产率提升={boost})")
        result = simulate(100, boost, 10)
        last = result[-1]
        print(f"  10年后:")
        print(f"    平均财富: {last['avg']:.0f}")
        print(f"    前10%占比: {last['top10_share']:.1%}")
        print(f"    后50%占比: {last['bottom50_share']:.1%}")
        print(f"    基尼系数:  {last['gini']:.3f}")

    print("\n⚠️ 此模拟极其简化，仅供概念演示。")
    print("✅ AI 社会思考演示完成")


if __name__ == "__main__":
    main()
