#!/usr/bin/env python3
"""
MVC 模式游戏演示 — Model/View/Controller 分离
纯标准库，直接运行。

架构：
  Model  — 角色数据（血量、等级、位置），纯数据 + 业务规则
  View   — 终端 UI 渲染，只读 Model，不修改数据
  Controller — 处理用户输入，调用 Model 方法
"""

import random
import sys
import time
import threading


# ─── Model ───────────────────────────────────────────────────────
class CharacterModel:
    """角色数据模型：持有状态，提供业务方法"""

    def __init__(self, name: str):
        self.name = name
        self.hp = 100
        self.max_hp = 100
        self.level = 1
        self.exp = 0
        self.x = 0
        self.y = 0
        self.gold = 50
        self.inventory: list[str] = []

    # 观察者列表 — 当数据变化时通知 View
    def __init_subclass__(self):
        pass

    def move(self, dx: int, dy: int) -> str:
        self.x += dx
        self.y += dy
        return f"移动到 ({self.x}, {self.y})"

    def take_damage(self, amount: int) -> str:
        self.hp = max(0, self.hp - amount)
        return f"受到 {amount} 点伤害 (HP: {self.hp}/{self.max_hp})"

    def heal(self, amount: int) -> str:
        healed = min(amount, self.max_hp - self.hp)
        if healed == 0:
            return "HP已满，无需治疗"
        self.hp += healed
        return f"恢复 {healed} 点生命 (HP: {self.hp}/{self.max_hp})"

    def gain_exp(self, amount: int) -> str:
        self.exp += amount
        needed = self.level * 20
        if self.exp >= needed:
            self.exp -= needed
            self.level += 1
            self.max_hp += 20
            self.hp = self.max_hp
            return f"升级！Lv.{self.level} (HP上限+20)"
        return f"获得 {amount} EXP ({self.exp}/{needed})"

    def add_item(self, item: str) -> str:
        self.inventory.append(item)
        return f"获得物品: {item}"


# ─── Observer Pattern ────────────────────────────────────────────
class ObservableModel(CharacterModel):
    """带观察者通知的 Model 扩展"""

    def __init__(self, name: str):
        super().__init__(name)
        self._observers: list = []

    def attach(self, observer):
        self._observers.append(observer)

    def detach(self, observer):
        self._observers.remove(observer)

    def _notify(self, event: str = ""):
        for obs in self._observers:
            obs.on_model_changed(self, event)

    def move(self, dx, dy):
        result = super().move(dx, dy)
        self._notify("move")
        return result

    def take_damage(self, amount):
        result = super().take_damage(amount)
        self._notify("damage")
        return result

    def heal(self, amount):
        result = super().heal(amount)
        self._notify("heal")
        return result

    def gain_exp(self, amount):
        result = super().gain_exp(amount)
        self._notify("exp")
        return result

    def add_item(self, item):
        result = super().add_item(item)
        self._notify("item")
        return result


# ─── View ────────────────────────────────────────────────────────
class ConsoleView:
    """终端视图：纯展示，不修改 Model"""

    def __init__(self, model: ObservableModel):
        self.model = model
        model.attach(self)

    def on_model_changed(self, model: ObservableModel, event: str):
        """当 Model 变化时更新视图"""
        self.render()

    def render(self):
        """渲染角色状态面板"""
        m = self.model
        hp_bar = "█" * (m.hp // 5) + "░" * ((m.max_hp - m.hp) // 5)
        print(f"""
╔══════════════════════════════╗
║  {m.name:^24s}  ║
╠══════════════════════════════╣
║  Lv.{m.level:<3}  EXP: {m.exp:>3}/{m.level*20:<3}              ║
║  HP: [{hp_bar:>20s}] ║
║  HP: {m.hp:>3}/{m.max_hp:>3}                      ║
║  Gold: {m.gold:>4d}                        ║
║  位置: ({m.x:>3d}, {m.y:>3d})                  ║
║  背包: {len(m.inventory):>2d} 件                       ║
╚══════════════════════════════╝
""")


# ─── Controller ──────────────────────────────────────────────────
class InputController:
    """输入控制器：解析命令并调用 Model"""

    COMMANDS = {
        "w": ("向北移动", lambda m: m.move(0, 1)),
        "s": ("向南移动", lambda m: m.move(0, -1)),
        "a": ("向西移动", lambda m: m.move(-1, 0)),
        "d": ("向东移动", lambda m: m.move(1, 0)),
        "f": ("战斗 (随机)", lambda m: m.take_damage(random.randint(5, 25))),
        "h": ("治疗", lambda m: m.heal(random.randint(10, 30))),
        "k": ("打怪得经验", lambda m: m.gain_exp(random.randint(8, 18))),
        "i": ("随机物品", lambda m: m.add_item(random.choice(["药水", "铁剑", "盾牌", "卷轴", "金币袋"]))),
        "q": ("退出", None),
    }

    def __init__(self, model: ObservableModel):
        self.model = model

    def show_help(self):
        print("\n┌────────── 操作 ──────────┐")
        for key, (desc, _) in self.COMMANDS.items():
            print(f"│  [{key}] {desc:<22s} │")
        print("└─────────────────────────┘")

    def execute(self, cmd: str) -> bool:
        """执行命令，返回 False 表示退出"""
        cmd = cmd.strip().lower()
        if cmd not in self.COMMANDS:
            print(f"未知命令: {cmd}（输入 ? 查看帮助）")
            return True

        desc, action = self.COMMANDS[cmd]
        if action is None:
            print("再见！")
            return False

        result = action(self.model)
        print(f"\n>>> {result}")
        return True


# ─── Main ────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  MVC 模式演示 — Model / View / Controller")
    print("=" * 50)

    # 创建 Model
    model = ObservableModel("勇者")

    # 创建 View（自动注册为观察者）
    view = ConsoleView(model)

    # 创建 Controller
    controller = InputController(model)

    # 初始渲染
    view.render()
    controller.show_help()

    print("\n输入命令 (q=退出): ")
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not cmd:
            continue
        if not controller.execute(cmd):
            break


if __name__ == "__main__":
    main()
