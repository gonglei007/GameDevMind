"""
一个完整的控制台迷你RPG游戏

对应文章：七-05-一站式手游创业
"""

import random
from dataclasses import dataclass


@dataclass
class Player:
    name: str
    hp: int = 100
    max_hp: int = 100
    atk: int = 15
    defense: int = 5
    gold: int = 0
    level: int = 1
    exp: int = 0

    @property
    def alive(self): return self.hp > 0

    def attack(self, enemy: "Enemy") -> int:
        dmg = max(1, self.atk - enemy.defense + random.randint(-3, 3))
        crit = random.random() < 0.15
        if crit:
            dmg = int(dmg * 1.5)
            print("  💥 暴击！", end=" ")
        enemy.hp -= dmg
        return dmg

    def heal(self):
        heal = random.randint(15, 30)
        self.hp = min(self.max_hp, self.hp + heal)
        print(f"  💚 恢复 {heal} HP")

    def gain_exp(self, amount: int):
        self.exp += amount
        if self.exp >= self.level * 20:
            self.level += 1
            self.exp = 0
            self.max_hp += 15
            self.hp = self.max_hp
            self.atk += 3
            self.defense += 1
            print(f"  🎉 升级！Lv.{self.level}")


@dataclass
class Enemy:
    name: str
    hp: int
    atk: int
    defense: int

    @property
    def alive(self): return self.hp > 0

    def attack(self, player: Player) -> int:
        dmg = max(1, self.atk - player.defense + random.randint(-2, 2))
        player.hp -= dmg
        return dmg


ENEMIES = [
    Enemy("史莱姆", 30, 8, 2),
    Enemy("哥布林", 50, 12, 4),
    Enemy("骷髅兵", 70, 15, 6),
    Enemy("暗影法师", 60, 20, 3),
    Enemy("BOSS·黑龙", 120, 25, 10),
]


def battle(player: Player):
    enemy = random.choice(ENEMIES)
    print(f"\n⚔️  {enemy.name} 出现了！ (HP:{enemy.hp} ATK:{enemy.atk})")

    while player.alive and enemy.alive:
        print(f"\n  [你 HP:{player.hp}/{player.max_hp}] [敌人 HP:{max(0,enemy.hp)}]")
        print("  1.攻击  2.治疗  3.逃跑")
        choice = input("  选择: ").strip()

        if choice == "1":
            dmg = player.attack(enemy)
            print(f"造成 {dmg} 伤害")
        elif choice == "2":
            player.heal()
        elif choice == "3":
            if random.random() < 0.5:
                print("  成功逃跑！")
                return
            print("  逃跑失败！")

        if enemy.alive:
            dmg = enemy.attack(player)
            print(f"  {enemy.name} 造成 {dmg} 伤害")

    if player.alive:
        gold = random.randint(10, 30)
        exp = random.randint(10, 25)
        player.gold += gold
        print(f"  ✅ 胜利！+{gold}金币 +{exp}经验")
        player.gain_exp(exp)
    else:
        print(f"  💀 你被 {enemy.name} 击败了...")


def main():
    print("=" * 40)
    print("  ⚔️  迷你 RPG — 勇者斗恶龙 ⚔️")
    print("=" * 40)

    name = input("\n输入勇者名字: ").strip() or "勇者"
    player = Player(name)

    print(f"\n✨ {player.name} 踏上冒险之旅！")
    print(f"  HP:{player.hp} ATK:{player.atk} DEF:{player.defense}")

    for _ in range(3):
        if not player.alive:
            break
        battle(player)

    print(f"\n📊 冒险结束！")
    print(f"  等级: Lv.{player.level}")
    print(f"  金币: {player.gold}")
    print(f"  {'🎉 凯旋归来！' if player.alive else '💀 下次再来...'}")

    print("\n✅ 迷你游戏演示完成")


if __name__ == "__main__":
    main()
