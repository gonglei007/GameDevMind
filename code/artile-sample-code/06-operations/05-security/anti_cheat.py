#!/usr/bin/env python3
"""
反作弊检测系统 - 速度异常/数据篡改/心跳异常检测
文章: 06-operations/05-security (游戏安全与反作弊)
纯标准库，python3 直接运行
"""

import time
import random
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from enum import Enum


class CheatType(Enum):
    """作弊类型"""
    SPEED_HACK = "speed_hack"           # 速度异常（瞬移/加速）
    DATA_TAMPER = "data_tamper"         # 数据篡改
    HEARTBEAT_ANOMALY = "heartbeat"     # 心跳异常
    INJECTION = "injection"             # 内存注入
    REPLAY = "replay_attack"            # 重放攻击
    RESOURCE_ANOMALY = "resource"       # 资源异常（金币暴涨）
    COOLDOWN_BYPASS = "cooldown"        # 技能冷却绕过


@dataclass
class PlayerState:
    """玩家状态快照"""
    player_id: int
    x: float
    y: float
    timestamp: float
    hp: int
    mp: int
    gold: int
    level: int


@dataclass
class CheatAlert:
    """作弊警告"""
    player_id: int
    cheat_type: CheatType
    severity: float           # 0-1 严重程度
    evidence: Dict
    timestamp: float = field(default_factory=time.time)
    action_taken: str = ""


class AntiCheatEngine:
    """反作弊检测引擎"""

    # 配置
    MAX_SPEED = 500.0               # 最大移动速度（单位/秒）
    MAX_GOLD_PER_HOUR = 10000       # 每小时最大金币获取
    HEARTBEAT_INTERVAL = 5.0        # 预期心跳间隔（秒）
    HEARTBEAT_TOLERANCE = 3.0       # 心跳容差（秒）
    MAX_TELEPORT_DISTANCE = 3000.0  # 最大瞬移距离（容许合法传送）

    def __init__(self):
        # 玩家状态历史: player_id -> deque of PlayerState
        self.state_history: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        # 作弊记录
        self.alerts: List[CheatAlert] = []
        # 玩家可疑度评分: player_id -> float (0-100)
        self.suspicion_scores: Dict[int, float] = defaultdict(float)
        # 封禁列表
        self.banned_players: Dict[int, str] = {}
        # 心跳追踪
        self.last_heartbeat: Dict[int, float] = {}
        # 统计
        self.total_checks = 0
        self.total_detections = 0

    def submit_state(self, state: PlayerState) -> List[CheatAlert]:
        """
        提交玩家状态进行检查
        返回新触发的告警列表
        """
        self.total_checks += 1
        new_alerts = []

        # 获取历史
        history = self.state_history[state.player_id]

        # === 检查1: 速度异常检测 ===
        if len(history) >= 1:
            prev = history[-1]
            dt = state.timestamp - prev.timestamp
            if dt > 0.001:
                dx = state.x - prev.x
                dy = state.y - prev.y
                distance = math.sqrt(dx * dx + dy * dy)
                speed = distance / dt

                if speed > self.MAX_TELEPORT_DISTANCE / dt:
                    # 瞬移检测
                    alert = CheatAlert(
                        player_id=state.player_id,
                        cheat_type=CheatType.SPEED_HACK,
                        severity=min(1.0, speed / 5000),
                        evidence={
                            "speed": round(speed, 1),
                            "distance": round(distance, 1),
                            "dt": round(dt, 3),
                            "from": (prev.x, prev.y),
                            "to": (state.x, state.y),
                        }
                    )
                    new_alerts.append(alert)
                elif speed > self.MAX_SPEED:
                    # 超速检测
                    alert = CheatAlert(
                        player_id=state.player_id,
                        cheat_type=CheatType.SPEED_HACK,
                        severity=min(1.0, (speed - self.MAX_SPEED) / 500),
                        evidence={
                            "speed": round(speed, 1),
                            "max_allowed": self.MAX_SPEED,
                            "dt": round(dt, 3),
                        }
                    )
                    new_alerts.append(alert)

        # === 检查2: 资源异常检测 ===
        if len(history) >= 2:
            # 金币暴涨检测
            recent = list(history)[-10:]
            if recent:
                gold_gain = state.gold - recent[0].gold
                time_span_hours = (state.timestamp - recent[0].timestamp) / 3600
                if time_span_hours > 0 and gold_gain / time_span_hours > self.MAX_GOLD_PER_HOUR:
                    alert = CheatAlert(
                        player_id=state.player_id,
                        cheat_type=CheatType.RESOURCE_ANOMALY,
                        severity=min(1.0, gold_gain / (self.MAX_GOLD_PER_HOUR * time_span_hours * 2)),
                        evidence={
                            "gold_gain": gold_gain,
                            "time_hours": round(time_span_hours, 2),
                            "rate": round(gold_gain / time_span_hours, 1),
                            "max_rate": self.MAX_GOLD_PER_HOUR,
                        }
                    )
                    new_alerts.append(alert)

            # 等级异常（瞬间跳多级）
            level_gain = state.level - history[-1].level
            if level_gain > 2:
                alert = CheatAlert(
                    player_id=state.player_id,
                    cheat_type=CheatType.DATA_TAMPER,
                    severity=min(1.0, level_gain / 10),
                    evidence={
                        "level_jump": level_gain,
                        "from_level": history[-1].level,
                        "to_level": state.level,
                    }
                )
                new_alerts.append(alert)

        # === 检查3: 心跳异常检测 ===
        if state.player_id in self.last_heartbeat:
            elapsed = state.timestamp - self.last_heartbeat[state.player_id]
            if elapsed > self.HEARTBEAT_INTERVAL + self.HEARTBEAT_TOLERANCE:
                alert = CheatAlert(
                    player_id=state.player_id,
                    cheat_type=CheatType.HEARTBEAT_ANOMALY,
                    severity=min(1.0, (elapsed - self.HEARTBEAT_INTERVAL) / 30),
                    evidence={
                        "elapsed": round(elapsed, 2),
                        "expected": self.HEARTBEAT_INTERVAL,
                        "tolerance": self.HEARTBEAT_TOLERANCE,
                    }
                )
                new_alerts.append(alert)

        self.last_heartbeat[state.player_id] = state.timestamp

        # 更新可疑度
        for alert in new_alerts:
            self.suspicion_scores[state.player_id] += alert.severity * 10
            # 自动封禁
            if self.suspicion_scores[state.player_id] > 80:
                alert.action_taken = "auto_ban"
                self.banned_players[state.player_id] = (
                    f"可疑度 {self.suspicion_scores[state.player_id]:.0f}/100，"
                    f"最后检测: {alert.cheat_type.value}"
                )

        # 保存状态
        history.append(state)
        self.alerts.extend(new_alerts)
        self.total_detections += len(new_alerts)

        return new_alerts

    def get_suspicion_report(self) -> str:
        """获取可疑玩家报告"""
        if not self.suspicion_scores:
            return "📊 无可疑玩家"

        # 按可疑度排序
        sorted_players = sorted(
            self.suspicion_scores.items(),
            key=lambda x: -x[1]
        )

        lines = ["=" * 55]
        lines.append("  🚨 玩家可疑度报告")
        lines.append("=" * 55)
        lines.append(f"  {'玩家ID':<10} {'可疑度':<10} {'状态':<12} {'最近检测'}")
        lines.append(f"  {'-'*10} {'-'*10} {'-'*12} {'-'*20}")

        for pid, score in sorted_players[:10]:
            status = "🔴 已封禁" if pid in self.banned_players else (
                "🟡 监控中" if score > 40 else "🟢 正常"
            )
            # 找到最新告警类型
            recent_alerts = [a for a in reversed(self.alerts) if a.player_id == pid]
            recent_type = recent_alerts[0].cheat_type.value if recent_alerts else "-"
            lines.append(f"  {pid:<10} {score:<10.1f} {status:<12} {recent_type}")

        lines.append(f"\n  总检测: {self.total_checks} | 命中: {self.total_detections}")
        lines.append(f"  封禁: {len(self.banned_players)} | 告警: {len(self.alerts)}")
        return "\n".join(lines)

    def player_status(self, player_id: int) -> Dict:
        """查询单个玩家状态"""
        history = self.state_history.get(player_id, deque())
        return {
            "player_id": player_id,
            "suspicion": round(self.suspicion_scores[player_id], 1),
            "banned": player_id in self.banned_players,
            "ban_reason": self.banned_players.get(player_id, ""),
            "state_count": len(history),
            "latest_state": history[-1] if history else None,
            "alert_count": sum(1 for a in self.alerts if a.player_id == player_id),
        }


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  反作弊检测系统 - 演示")
    print("=" * 60)

    engine = AntiCheatEngine()
    base_time = time.time()

    # 模拟正常玩家
    print("\n👤 模拟正常玩家 (ID=1001):")
    normal_states = [
        PlayerState(1001, 100.0 + i * 3, 200.0 + i * 2,
                    base_time + i * 5, 1000 - i, 500 - i * 2,
                    1000 + i * 10, 5 + i // 20)
        for i in range(10)
    ]
    for state in normal_states:
        engine.submit_state(state)
    print(f"  提交 {len(normal_states)} 个状态快照，检测告警: {engine.total_detections}")
    print(f"  玩家1001 可疑度: {engine.suspicion_scores[1001]:.1f}")

    # 模拟速度黑客
    print("\n🚀 模拟速度黑客 (ID=9998):")
    hack_states = [
        PlayerState(9998, 0.0, 0.0, base_time + 0, 1000, 500, 1000, 10),
        PlayerState(9998, 5000.0, 5000.0, base_time + 1, 1000, 500, 1000, 10),  # 瞬移!
        PlayerState(9998, 10000.0, 10000.0, base_time + 2, 1000, 500, 1000, 10),
    ]
    for state in hack_states:
        alerts = engine.submit_state(state)
        if alerts:
            for a in alerts:
                print(f"  🚨 检测到 {a.cheat_type.value}! 严重度: {a.severity:.2f}")
                print(f"     证据: {a.evidence}")
    print(f"  玩家9998 可疑度: {engine.suspicion_scores[9998]:.1f}")

    # 模拟资源异常
    print("\n💰 模拟金币异常 (ID=9997):")
    resource_states = [
        PlayerState(9997, 50.0, 50.0, base_time + 0, 1000, 500, 1000, 10),
        PlayerState(9997, 55.0, 55.0, base_time + 60, 1000, 500, 50000, 10),  # 金币暴涨!
        PlayerState(9997, 60.0, 60.0, base_time + 120, 1000, 500, 100000, 10),
    ]
    for state in resource_states:
        alerts = engine.submit_state(state)
        if alerts:
            for a in alerts:
                print(f"  🚨 检测到 {a.cheat_type.value}! 严重度: {a.severity:.2f}")
                print(f"     证据: {a.evidence}")
    print(f"  玩家9997 可疑度: {engine.suspicion_scores[9997]:.1f}")

    # 模拟心跳异常
    print("\n⏰ 模拟心跳异常 (ID=9996):")
    heartbeat_states = [
        PlayerState(9996, 10.0, 10.0, base_time + 0, 1000, 500, 500, 5),
        PlayerState(9996, 12.0, 12.0, base_time + 5, 1000, 500, 500, 5),
        PlayerState(9996, 14.0, 14.0, base_time + 30, 1000, 500, 500, 5),  # 心跳间隔过长!
    ]
    for state in heartbeat_states:
        alerts = engine.submit_state(state)
        if alerts:
            for a in alerts:
                print(f"  🚨 检测到 {a.cheat_type.value}! 严重度: {a.severity:.2f}")
                print(f"     证据: {a.evidence}")

    # 报告
    print("\n" + engine.get_suspicion_report())

    # 单个玩家详情
    print("\n🔍 玩家9998 详细状态:")
    status = engine.player_status(9998)
    for k, v in status.items():
        if k != "latest_state":
            print(f"  {k}: {v}")

    print("\n✅ 反作弊检测演示完成!")


if __name__ == "__main__":
    run_demo()
