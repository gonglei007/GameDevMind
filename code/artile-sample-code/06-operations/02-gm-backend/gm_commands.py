#!/usr/bin/env python3
"""
GM命令系统 - 命令注册/执行/权限/日志
文章: 06-operations/02-gm-backend (GM后台与命令系统)
纯标准库，python3 直接运行
"""

import json
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from enum import Enum


class Permission(Enum):
    """GM权限级别"""
    PLAYER = 0       # 玩家自用命令
    MODERATOR = 1    # 客服/版主
    GM = 2           # 游戏管理员
    ADMIN = 3        # 超级管理员
    DEVELOPER = 4    # 开发者


@dataclass
class GMCommand:
    """GM命令定义"""
    name: str
    description: str
    handler: Callable
    permission: Permission = Permission.GM
    params: List[str] = field(default_factory=list)  # 参数名列表
    cooldown_seconds: float = 0  # 冷却时间（秒）


@dataclass
class CommandLog:
    """命令执行日志"""
    timestamp: float
    gm_name: str
    command: str
    params: List[Any]
    result: Any
    success: bool
    error: Optional[str] = None


# ============================================================
# 模拟游戏世界状态
# ============================================================
class GameWorld:
    """模拟的游戏世界"""

    def __init__(self):
        self.players: Dict[int, Dict] = {
            1001: {"name": "勇者小明", "level": 42, "gold": 5000, "diamond": 120,
                   "vip_level": 3, "banned": False},
            1002: {"name": "法师小红", "level": 38, "gold": 3200, "diamond": 80,
                   "vip_level": 1, "banned": False},
            1003: {"name": "刺客小黑", "level": 55, "gold": 15000, "diamond": 500,
                   "vip_level": 5, "banned": False},
        }
        self.items: Dict[int, Dict] = {
            2001: {"name": "传说之剑", "price": 5000, "stock": 10},
            2002: {"name": "生命药水", "price": 50, "stock": 999},
            2003: {"name": "强化石", "price": 200, "stock": 500},
        }
        self.server_announcements: List[str] = []
        self._item_id_counter = 2004

    def get_player(self, player_id: int) -> Optional[Dict]:
        return self.players.get(player_id)

    def add_gold(self, player_id: int, amount: int) -> str:
        player = self.get_player(player_id)
        if not player:
            return f"玩家 {player_id} 不存在"
        player["gold"] += amount
        return f"玩家 {player['name']}({player_id}) 获得 {amount} 金币，现有 {player['gold']}"

    def add_item(self, player_id: int, item_id: int, count: int) -> str:
        player = self.get_player(player_id)
        if not player:
            return f"玩家 {player_id} 不存在"
        item = self.items.get(item_id)
        if not item:
            return f"物品 {item_id} 不存在"
        return f"已为玩家 {player['name']}({player_id}) 发放 {item['name']} x{count}"

    def ban_player(self, player_id: int, reason: str) -> str:
        player = self.get_player(player_id)
        if not player:
            return f"玩家 {player_id} 不存在"
        player["banned"] = True
        return f"已封禁玩家 {player['name']}({player_id})，原因: {reason}"

    def unban_player(self, player_id: int) -> str:
        player = self.get_player(player_id)
        if not player:
            return f"玩家 {player_id} 不存在"
        player["banned"] = False
        return f"已解封玩家 {player['name']}({player_id})"

    def broadcast(self, message: str) -> str:
        self.server_announcements.append(message)
        return f"全服公告已发送: {message}"

    def online_count(self) -> str:
        import random
        return f"当前在线: {random.randint(500, 5000)} 人"


# ============================================================
# GM 命令系统
# ============================================================
class GMSystem:
    """GM命令管理系统"""

    def __init__(self):
        self.commands: Dict[str, GMCommand] = {}
        self.logs: List[CommandLog] = []
        self._last_use: Dict[str, float] = {}
        self.world = GameWorld()

        self._register_default_commands()

    def _register_default_commands(self):
        """注册内置GM命令"""
        # 查询命令 (MODERATOR+)
        self.register(GMCommand(
            "lookup_player", "查询玩家信息",
            lambda args: self.world.get_player(int(args[0])),
            Permission.MODERATOR, ["player_id"]
        ))
        self.register(GMCommand(
            "online_count", "查看在线人数",
            lambda args: self.world.online_count(),
            Permission.MODERATOR, []
        ))

        # 操作命令 (GM+)
        self.register(GMCommand(
            "add_gold", "给玩家增加金币",
            lambda args: self.world.add_gold(int(args[0]), int(args[1])),
            Permission.GM, ["player_id", "amount"], cooldown_seconds=5
        ))
        self.register(GMCommand(
            "add_item", "给玩家发放物品",
            lambda args: self.world.add_item(int(args[0]), int(args[1]), int(args[2])),
            Permission.GM, ["player_id", "item_id", "count"], cooldown_seconds=3
        ))
        self.register(GMCommand(
            "ban_player", "封禁玩家",
            lambda args: self.world.ban_player(int(args[0]), args[1] if len(args) > 1 else "违规行为"),
            Permission.GM, ["player_id", "reason?"]
        ))
        self.register(GMCommand(
            "unban_player", "解封玩家",
            lambda args: self.world.unban_player(int(args[0])),
            Permission.GM, ["player_id"]
        ))

        # 管理命令 (ADMIN+)
        self.register(GMCommand(
            "broadcast", "发送全服公告",
            lambda args: self.world.broadcast(" ".join(args)),
            Permission.ADMIN, ["message"]
        ))
        self.register(GMCommand(
            "list_commands", "列出可用命令",
            lambda args: self._list_commands(int(args[0]) if args else 0),
            Permission.MODERATOR, ["permission_level?"]
        ))

    def register(self, cmd: GMCommand):
        """注册命令"""
        self.commands[cmd.name] = cmd

    def _list_commands(self, perm_level: int = 0) -> str:
        """列出可用命令"""
        available = [c for c in self.commands.values()
                     if c.permission.value <= perm_level]
        lines = ["可用命令:"]
        for c in available:
            params = " ".join(f"<{p}>" for p in c.params)
            lines.append(f"  /{c.name} {params}  [{c.permission.name}] {c.description}")
        return "\n".join(lines)

    def execute(self, gm_name: str, permission: Permission,
                command_name: str, args: List[str]) -> Dict:
        """
        执行GM命令
        返回: {"success": bool, "result": Any, "error": str|None}
        """
        # 查找命令
        cmd = self.commands.get(command_name)
        if not cmd:
            return self._log_and_return(gm_name, command_name, args,
                                        False, None, f"未知命令: {command_name}")

        # 权限检查
        if permission.value < cmd.permission.value:
            return self._log_and_return(gm_name, command_name, args, False, None,
                                        f"权限不足! 需要 {cmd.permission.name}，当前 {permission.name}")

        # 冷却检查
        if cmd.cooldown_seconds > 0:
            cooldown_key = f"{gm_name}:{command_name}"
            last_use = self._last_use.get(cooldown_key, 0)
            elapsed = time.time() - last_use
            if elapsed < cmd.cooldown_seconds:
                remaining = cmd.cooldown_seconds - elapsed
                return self._log_and_return(gm_name, command_name, args, False, None,
                                            f"冷却中! 请等待 {remaining:.1f} 秒")

            self._last_use[cooldown_key] = time.time()

        # 执行命令
        try:
            result = cmd.handler(args)
            return self._log_and_return(gm_name, command_name, args, True, result)
        except Exception as e:
            return self._log_and_return(gm_name, command_name, args,
                                        False, None, f"执行异常: {str(e)}")

    def _log_and_return(self, gm_name: str, cmd: str, params: List,
                        success: bool, result: Any,
                        error: Optional[str] = None) -> Dict:
        """记录日志并返回"""
        log = CommandLog(
            timestamp=time.time(),
            gm_name=gm_name,
            command=cmd,
            params=params,
            result=result,
            success=success,
            error=error
        )
        self.logs.append(log)
        return {"success": success, "result": result or error, "error": error}

    def get_recent_logs(self, count: int = 20) -> List[CommandLog]:
        """获取最近日志"""
        return self.logs[-count:]

    def audit_report(self) -> str:
        """生成审计报告"""
        if not self.logs:
            return "无操作记录"

        # 按GM分组统计
        gm_stats: Dict[str, int] = {}
        for log in self.logs:
            gm_stats[log.gm_name] = gm_stats.get(log.gm_name, 0) + 1

        lines = ["========== GM 操作审计报告 =========="]
        lines.append(f"总操作数: {len(self.logs)}")
        lines.append(f"成功: {sum(1 for l in self.logs if l.success)}")
        lines.append(f"失败: {sum(1 for l in self.logs if not l.success)}")
        lines.append("\n按GM统计:")
        for name, count in sorted(gm_stats.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count} 次")
        lines.append("\n最近10条操作:")
        for log in self.logs[-10:]:
            status = "✅" if log.success else "❌"
            dt = datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S")
            lines.append(f"  [{dt}] {status} {log.gm_name}: /{log.command} "
                         f"{log.params} -> {log.result}")
        return "\n".join(lines)


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  游戏GM命令系统 - 演示")
    print("=" * 60)

    gm = GMSystem()

    # 模拟GM操作序列
    operations = [
        # (GM名称, 权限, 命令, 参数)
        ("客服小王", Permission.MODERATOR, "lookup_player", ["1001"]),
        ("客服小王", Permission.MODERATOR, "lookup_player", ["9999"]),
        ("客服小王", Permission.MODERATOR, "online_count", []),
        ("客服小王", Permission.MODERATOR, "ban_player", ["1003"]),  # 权限不足

        ("管理员老张", Permission.GM, "add_gold", ["1001", "1000"]),
        ("管理员老张", Permission.GM, "add_item", ["1002", "2001", "1"]),
        ("管理员老张", Permission.GM, "ban_player", ["1003", "使用外挂"]),

        ("超级管理", Permission.ADMIN, "broadcast",
         ["服务器将于22:00进行维护，请提前下线"]),
        ("超级管理", Permission.ADMIN, "unban_player", ["1003"]),
    ]

    print("\n🎮 模拟GM操作序列:\n")
    for gm_name, perm, cmd, args in operations:
        result = gm.execute(gm_name, perm, cmd, args)
        icon = "✅" if result["success"] else "❌"
        print(f"  {icon} [{perm.name}] {gm_name}: /{cmd} {args}")
        print(f"     -> {result['result']}")

    # 审计报告
    print("\n" + gm.audit_report())

    # 命令列表
    print("\n📋 所有注册命令:")
    for name, cmd in gm.commands.items():
        params = " ".join(f"<{p}>" for p in cmd.params)
        print(f"  /{name} {params}")
        print(f"     权限: {cmd.permission.name} | {cmd.description}")

    print("\n✅ GM命令系统演示完成!")


if __name__ == "__main__":
    run_demo()
