"""
游戏创业预算计算器

对应文章：七-03-游戏创业指南
"""

def calc_budget(team_size: int, months: int, office: bool = True):
    salary_avg = 20000  # 人均月薪
    office_cost = 15000 if office else 0
    server_cost = 5000
    marketing = 50000

    total_salary = salary_avg * team_size * months
    total_office = office_cost * months
    total_server = server_cost * months
    total = total_salary + total_office + total_server + marketing

    return {
        "人力成本": total_salary,
        "办公场地": total_office,
        "服务器": total_server,
        "推广预算": marketing,
        "总计": total
    }

def main():
    print("=== 游戏创业预算计算器 ===\n")

    scenarios = [
        ("最小MVP (3人×2月, 远程)", 3, 2, False),
        ("小团队 (5人×4月, 租场地)", 5, 4, True),
        ("标准团队 (10人×8月)", 10, 8, True),
    ]

    for name, team, months, office in scenarios:
        budget = calc_budget(team, months, office)
        print(f"📊 {name}")
        for k, v in budget.items():
            print(f"  {k}: ¥{v:,}")
        print(f"  人均月成本: ¥{budget['总计']/team/months:,.0f}")
        print()

    print("💡 建议：先用 MVP 验证玩法，再追加投入。")

if __name__ == "__main__":
    main()
