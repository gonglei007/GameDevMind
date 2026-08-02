#!/usr/bin/env python3
"""
热更新模拟 - Lua脚本加载/卸载/版本管理
文章: 06-operations/04-hotupdate (游戏热更新技术)
纯标准库，python3 直接运行

模拟Lua脚本的热更新流程：脚本注册→加载→运行时替换→版本回滚
"""

import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Tuple
from enum import Enum


# ============================================================
# 模拟的 "Lua 脚本" — 用Python函数模拟Lua行为
# ============================================================
@dataclass
class LuaScript:
    """模拟的Lua脚本"""
    name: str                    # 脚本名（如 "combat_damage.lua"）
    version: int                 # 版本号
    content_hash: str            # 内容哈希
    code: Callable              # 脚本逻辑（Python函数模拟）
    dependencies: List[str] = field(default_factory=list)  # 依赖的脚本名
    created_at: float = field(default_factory=time.time)


class ScriptStatus(Enum):
    LOADED = "loaded"
    RUNNING = "running"
    UNLOADED = "unloaded"
    ERROR = "error"


@dataclass
class ScriptInstance:
    """已加载的脚本实例"""
    script: LuaScript
    status: ScriptStatus = ScriptStatus.LOADED
    load_time: float = field(default_factory=time.time)
    error_message: Optional[str] = None


# ============================================================
# 热更新管理器
# ============================================================
class HotReloadManager:
    """Lua脚本热更新管理器"""

    def __init__(self):
        self.scripts: Dict[str, List[LuaScript]] = {}      # 脚本名 -> 版本列表
        self.loaded: Dict[str, ScriptInstance] = {}         # 脚本名 -> 当前实例
        self._version_counter: Dict[str, int] = {}          # 脚本名 -> 当前版本号
        self.update_log: List[Dict] = []                    # 更新日志
        self._callbacks: List[Callable] = []                # 脚本变更回调

    def register_script(self, script: LuaScript):
        """注册/提交新版本脚本"""
        if script.name not in self.scripts:
            self.scripts[script.name] = []
            self._version_counter[script.name] = 0

        # 分配版本号
        if script.version == 0:
            self._version_counter[script.name] += 1
            script.version = self._version_counter[script.name]

        # 计算哈希
        if not script.content_hash:
            content = script.code.__code__.co_code if hasattr(script.code, '__code__') else str(id(script.code))
            script.content_hash = hashlib.md5(str(content).encode()).hexdigest()[:8]

        # 检查重复版本
        for existing in self.scripts[script.name]:
            if existing.content_hash == script.content_hash:
                print(f"  ⚠️  脚本 {script.name} v{script.version} 内容与 v{existing.version} 相同，跳过")
                return

        self.scripts[script.name].append(script)
        self.update_log.append({
            "time": time.time(),
            "action": "registered",
            "script": script.name,
            "version": script.version,
            "hash": script.content_hash,
        })

    def load_script(self, name: str, version: Optional[int] = None) -> bool:
        """
        加载脚本到运行时
        version=None: 加载最新版本
        """
        if name not in self.scripts or not self.scripts[name]:
            print(f"  ❌ 脚本 {name} 未注册")
            return False

        # 选择版本
        versions = self.scripts[name]
        if version is not None:
            target = next((s for s in versions if s.version == version), None)
            if not target:
                print(f"  ❌ 脚本 {name} v{version} 不存在")
                return False
        else:
            target = versions[-1]  # 最新版本

        # 检查依赖
        for dep in target.dependencies:
            if dep not in self.loaded or self.loaded[dep].status != ScriptStatus.RUNNING:
                print(f"  ⚠️  依赖 {dep} 未加载，尝试自动加载...")
                self.load_script(dep)

        # 卸载旧版本
        old_version = None
        if name in self.loaded:
            old_version = self.loaded[name].script.version

        # 加载新版本
        instance = ScriptInstance(script=target, status=ScriptStatus.LOADED)
        self.loaded[name] = instance
        instance.status = ScriptStatus.RUNNING

        self.update_log.append({
            "time": time.time(),
            "action": "loaded",
            "script": name,
            "version": target.version,
            "old_version": old_version,
            "hash": target.content_hash,
        })

        # 触发变更回调
        self._notify_callbacks(name, old_version, target.version)

        print(f"  ✅ 脚本 {name}: v{old_version or '-'} → v{target.version} (hash: {target.content_hash})")
        return True

    def unload_script(self, name: str) -> bool:
        """卸载脚本"""
        if name not in self.loaded:
            print(f"  ⚠️  脚本 {name} 未加载")
            return False

        self.loaded[name].status = ScriptStatus.UNLOADED
        old_version = self.loaded[name].script.version
        del self.loaded[name]

        self.update_log.append({
            "time": time.time(),
            "action": "unloaded",
            "script": name,
            "old_version": old_version,
        })
        print(f"  🗑️  脚本 {name} v{old_version} 已卸载")
        return True

    def rollback(self, name: str, target_version: int) -> bool:
        """回滚到指定版本"""
        if name not in self.scripts:
            print(f"  ❌ 脚本 {name} 不存在")
            return False

        return self.load_script(name, target_version)

    def get_status(self) -> Dict:
        """获取所有脚本状态"""
        result = {}
        for name in self.scripts:
            loaded_info = self.loaded.get(name)
            versions = [s.version for s in self.scripts[name]]
            result[name] = {
                "versions": sorted(versions),
                "latest": max(versions),
                "loaded": loaded_info.script.version if loaded_info else None,
                "status": loaded_info.status.value if loaded_info else "unloaded",
                "hash": loaded_info.script.content_hash if loaded_info else None,
            }
        return result

    def on_script_change(self, callback: Callable):
        """注册脚本变更回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, name: str, old_v: Optional[int], new_v: int):
        for cb in self._callbacks:
            try:
                cb(name, old_v, new_v)
            except Exception as e:
                print(f"  ⚠️  回调异常: {e}")

    def validate_dependencies(self) -> Dict[str, List[str]]:
        """校验所有脚本依赖是否满足"""
        issues = {}
        for name, instance in self.loaded.items():
            for dep in instance.script.dependencies:
                if dep not in self.loaded:
                    issues.setdefault(name, []).append(f"缺失依赖: {dep}")
                elif self.loaded[dep].status != ScriptStatus.RUNNING:
                    issues.setdefault(name, []).append(f"依赖未运行: {dep}")
        return issues


# ============================================================
# 模拟游戏逻辑脚本
# ============================================================
def combat_damage_v1(*args):
    """伤害计算 v1: 简单公式"""
    return {"formula": "atk * 1.0 - def * 0.5", "version": 1}

def combat_damage_v2(*args):
    """伤害计算 v2: 加入暴击"""
    return {"formula": "atk * (1.5 if crit else 1.0) - def * 0.5", "version": 2}

def combat_damage_v3(*args):
    """伤害计算 v3: 加入元素加成"""
    return {"formula": "atk * (1.5 if crit else 1.0) * element_bonus - def * 0.5", "version": 3}

def npc_ai_v1(*args):
    """NPC行为 v1: 随机巡逻"""
    return {"behavior": "patrol_random", "version": 1}

def npc_ai_v2(*args):
    """NPC行为 v2: 智能寻路"""
    return {"behavior": "pathfinding_a_star", "version": 2}

def reward_calc_v1(*args):
    """奖励计算 v1"""
    return {"formula": "base * (1 + vip_bonus)", "version": 1}


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  游戏热更新系统 - Lua脚本热重载演示")
    print("=" * 60)

    hrm = HotReloadManager()

    # 注册变更监听
    def on_change(name, old_v, new_v):
        print(f"     📢 [事件] 脚本 {name} 变更: v{old_v} → v{new_v}")

    hrm.on_script_change(on_change)

    # ====== 阶段1: 初始部署 ======
    print("\n📦 阶段1: 初始脚本部署")
    print("-" * 40)
    hrm.register_script(LuaScript("combat_damage", 0, "", combat_damage_v1))
    hrm.register_script(LuaScript("npc_ai", 0, "", npc_ai_v1))
    hrm.register_script(LuaScript("reward_calc", 0, "", reward_calc_v1,
                                  dependencies=["combat_damage"]))
    hrm.load_script("combat_damage")
    hrm.load_script("npc_ai")
    hrm.load_script("reward_calc")

    # ====== 阶段2: 热更新 ======
    print("\n🔄 阶段2: 热更新 - 不停服更新")
    print("-" * 40)
    print("  [运营] 发现伤害公式需要调整，加入暴击机制...")
    hrm.register_script(LuaScript("combat_damage", 0, "", combat_damage_v2))
    hrm.load_script("combat_damage")  # 热更新！

    print("\n  [策划] NPC AI 需要升级为智能寻路...")
    hrm.register_script(LuaScript("npc_ai", 0, "", npc_ai_v2))
    hrm.load_script("npc_ai")

    # ====== 阶段3: 问题回滚 ======
    print("\n⏪ 阶段3: 紧急回滚")
    print("-" * 40)
    print("  [报警] 暴击公式伤害过高! 立即回滚到 v1...")
    hrm.rollback("combat_damage", 1)

    # ====== 阶段4: 修复后再更新 ======
    print("\n🔧 阶段4: 修复后重新上线")
    print("-" * 40)
    print("  [开发] 修复伤害公式，加入元素加成...")
    hrm.register_script(LuaScript("combat_damage", 0, "", combat_damage_v3))
    hrm.load_script("combat_damage")

    # ====== 状态展示 ======
    print("\n" + "=" * 60)
    print("📊 当前脚本状态:")
    print("-" * 60)
    status = hrm.get_status()
    print(f"  {'脚本名':<20} {'版本列表':<15} {'当前版本':<10} {'状态':<12} {'Hash':<10}")
    print(f"  {'-'*20} {'-'*15} {'-'*10} {'-'*12} {'-'*10}")
    for name, info in status.items():
        versions = ",".join(f"v{v}" for v in info['versions'])
        current = f"v{info['loaded']}" if info['loaded'] else "-"
        print(f"  {name:<20} {versions:<15} {current:<10} {info['status']:<12} {info['hash'] or '-':<10}")

    # 依赖校验
    print("\n🔍 依赖校验:")
    issues = hrm.validate_dependencies()
    if issues:
        for name, deps in issues.items():
            print(f"  ⚠️  {name}: {', '.join(deps)}")
    else:
        print("  ✅ 所有依赖正常")

    # 更新日志摘要
    print("\n📝 操作日志:")
    for log in hrm.update_log:
        dt = datetime.fromtimestamp(log['time']).strftime("%H:%M:%S")
        action_map = {"registered": "📝 注册", "loaded": "🔄 加载", "unloaded": "🗑️  卸载"}
        action = action_map.get(log['action'], log['action'])
        old = f" (旧: v{log['old_version']})" if log.get('old_version') else ""
        print(f"  [{dt}] {action}: {log['script']} v{log['version']}{old}")

    print("\n✅ 热更新演示完成!")


if __name__ == "__main__":
    run_demo()
