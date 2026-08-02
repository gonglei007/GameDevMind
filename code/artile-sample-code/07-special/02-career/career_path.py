"""
程序员职业发展路径模拟

对应文章：七-02-程序员职业发展路径
"""

CAREER_LADDER = [
    ("初级工程师",  0,  2,  "8-15K",   "执行任务，学习基础"),
    ("中级工程师",  2,  5,  "15-30K",  "独立负责模块"),
    ("高级工程师",  5,  8,  "30-50K",  "技术方案设计"),
    ("技术专家",    8,  12, "50-80K",  "跨团队技术决策"),
    ("架构师",     10, 15, "60-100K", "全公司技术架构"),
    ("技术总监",   12, 20, "80K+",    "技术团队管理"),
]

def simulate(years: int):
    print(f"\n📈 工作 {years} 年的职业路径:\n")
    print(f"{'职级':<12} {'年限范围':<10} {'薪资范围':<12} {'职责'}")
    print("-" * 60)
    for title, y_min, y_max, salary, duty in CAREER_LADDER:
        marker = " ← 当前位置" if y_min <= years <= y_max else ""
        print(f"{title:<12} {y_min}-{y_max}年    {salary:<12} {duty}{marker}")

def main():
    print("=== 程序员职业发展路径 ===\n")
    for y in [1, 3, 6, 10]:
        simulate(y)

if __name__ == "__main__":
    main()
