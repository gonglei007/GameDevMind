"""
游戏开发学习路线图生成器

对应文章：七-01-游戏开发新人指南
"""

SKILL_TREE = {
    "客户端开发": [
        ("C#/C++基础", 30, "必备"),
        ("Unity/Unreal入门", 60, "必备"),
        ("图形学基础", 40, "进阶"),
        ("性能优化", 30, "进阶"),
        ("Shader编写", 40, "高级"),
    ],
    "服务端开发": [
        ("Go/Java/C++基础", 30, "必备"),
        ("网络协议(TCP/UDP)", 20, "必备"),
        ("数据库(MySQL/Redis)", 30, "必备"),
        ("分布式系统", 40, "进阶"),
        ("容器化/K8s", 30, "高级"),
    ],
    "技术美术": [
        ("3D建模基础", 40, "必备"),
        ("Shader/材质", 50, "必备"),
        ("Houdini程序化", 60, "进阶"),
        ("渲染管线定制", 50, "高级"),
    ],
}

def generate_path(role: str):
    skills = SKILL_TREE.get(role, [])
    print(f"\n📚 {role} 学习路线图\n")
    total_days = 0
    print(f"{'技能':<20} {'天数':<8} {'等级':<8} {'进度'}")
    print("-" * 60)
    for name, days, level in skills:
        bar = "█" * (days // 10)
        print(f"{name:<20} {days:<8} {level:<8} {bar}")
        total_days += days
    print("-" * 60)
    print(f"{'总计':<20} {total_days} 天 ({total_days/30:.1f} 个月)")

def main():
    print("=== 游戏开发学习路线图 ===\n")
    print("可选岗位: 客户端开发 / 服务端开发 / 技术美术")

    for role in SKILL_TREE:
        generate_path(role)

    print("\n💡 建议：先完成'必备'技能即可开始做项目，边做边学进阶内容。")

if __name__ == "__main__":
    main()
