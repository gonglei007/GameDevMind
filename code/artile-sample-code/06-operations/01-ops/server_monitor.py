#!/usr/bin/env python3
"""
服务器监控模拟 - 模拟 CPU/内存/磁盘使用率监控 + 告警阈值
文章: 06-operations/01-ops (服务器运维监控)
纯标准库，python3 直接运行
"""

import random
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class AlertRule:
    """告警规则"""
    metric: str
    threshold: float      # 阈值（百分比）
    comparison: str       # 'gt' (> threshold) 或 'lt' (< threshold)
    severity: str         # 'warning' / 'critical'
    cooldown_seconds: int = 60  # 冷却时间


@dataclass
class Alert:
    """告警记录"""
    timestamp: float
    metric: str
    value: float
    threshold: float
    severity: str
    message: str


class ServerMonitor:
    """游戏服务器监控系统"""

    # 默认告警规则
    DEFAULT_RULES = [
        AlertRule("cpu_usage", 90, "gt", "critical", 30),
        AlertRule("cpu_usage", 75, "gt", "warning", 60),
        AlertRule("memory_usage", 95, "gt", "critical", 10),
        AlertRule("memory_usage", 85, "gt", "warning", 60),
        AlertRule("disk_usage", 90, "gt", "critical", 300),
        AlertRule("disk_usage", 80, "gt", "warning", 600),
        AlertRule("network_latency_ms", 200, "gt", "warning", 30),
        AlertRule("online_players", 100, "lt", "warning", 120),  # 玩家数过低
    ]

    def __init__(self, server_name: str = "game-server-01"):
        self.server_name = server_name
        self.rules: List[AlertRule] = list(self.DEFAULT_RULES)
        self.alerts: List[Alert] = []
        self.metrics_history: List[Dict] = []
        self._last_alert_time: Dict[str, float] = {}
        self._running = False

    def add_rule(self, rule: AlertRule):
        """添加自定义告警规则"""
        self.rules.append(rule)

    def _simulate_metrics(self) -> Dict:
        """模拟采集服务器指标"""
        return {
            "timestamp": time.time(),
            "server": self.server_name,
            "cpu_usage": round(random.gauss(55, 20), 1),
            "memory_usage": round(random.gauss(65, 15), 1),
            "disk_usage": round(random.gauss(70, 8), 1),
            "network_latency_ms": round(max(1, random.gauss(40, 30)), 1),
            "online_players": random.randint(50, 500),
            "requests_per_second": random.randint(100, 5000),
            "error_rate_pct": round(random.expovariate(1 / 0.5), 3),
        }

    def _check_rules(self, metrics: Dict) -> List[Alert]:
        """检查所有规则，返回触发的告警"""
        triggered = []
        now = time.time()

        for rule in self.rules:
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            triggered_flag = False

            if rule.comparison == "gt" and value > rule.threshold:
                triggered_flag = True
            elif rule.comparison == "lt" and value < rule.threshold:
                triggered_flag = True

            if not triggered_flag:
                continue

            # 冷却检查
            cooldown_key = f"{rule.metric}:{rule.severity}"
            last_time = self._last_alert_time.get(cooldown_key, 0)
            if now - last_time < rule.cooldown_seconds:
                continue

            self._last_alert_time[cooldown_key] = now

            alert = Alert(
                timestamp=now,
                metric=rule.metric,
                value=value,
                threshold=rule.threshold,
                severity=rule.severity,
                message=f"[{rule.severity.upper()}] {rule.metric}={value:.1f} "
                        f"(threshold: {rule.comparison} {rule.threshold})"
            )
            triggered.append(alert)

        return triggered

    def collect(self) -> Dict:
        """执行一次监控采集，返回采集结果和告警"""
        metrics = self._simulate_metrics()
        self.metrics_history.append(metrics)

        # 只保留最近 1000 条
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]

        new_alerts = self._check_rules(metrics)
        self.alerts.extend(new_alerts)

        return {
            "metrics": metrics,
            "alerts": [a.message for a in new_alerts],
            "total_alerts_today": len(self.alerts),
        }

    def get_status(self) -> Dict:
        """获取服务器当前状态摘要"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "尚未采集数据"}

        latest = self.metrics_history[-1]

        # 计算健康度评分 (0-100)
        health_score = 100.0
        if latest["cpu_usage"] > 90:
            health_score -= 30
        elif latest["cpu_usage"] > 70:
            health_score -= 10
        if latest["memory_usage"] > 90:
            health_score -= 30
        elif latest["memory_usage"] > 80:
            health_score -= 15
        if latest["disk_usage"] > 85:
            health_score -= 20
        if latest["error_rate_pct"] > 1:
            health_score -= 10

        health_score = max(0, min(100, health_score))

        # 状态判定
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "critical"

        return {
            "server": self.server_name,
            "status": status,
            "health_score": round(health_score, 1),
            "latest_metrics": latest,
            "recent_alerts": len([a for a in self.alerts
                                  if time.time() - a.timestamp < 3600]),
        }

    def get_alert_history(self, severity: Optional[str] = None) -> List[Alert]:
        """获取告警历史，可按严重级别过滤"""
        if severity:
            return [a for a in self.alerts if a.severity == severity]
        return list(self.alerts)


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  游戏服务器监控系统 - 演示")
    print("=" * 60)

    monitor = ServerMonitor("zhihu-game-01")

    # 模拟 10 轮采集
    print("\n📊 开始采集服务器指标 (模拟 10 轮)...\n")
    for i in range(10):
        result = monitor.collect()
        m = result["metrics"]
        status_icon = "🔴" if result["alerts"] else "🟢"
        print(f"  [{i+1:2d}] {status_icon} "
              f"CPU:{m['cpu_usage']:5.1f}%  "
              f"MEM:{m['memory_usage']:5.1f}%  "
              f"DISK:{m['disk_usage']:5.1f}%  "
              f"玩家:{m['online_players']}  "
              f"错误率:{m['error_rate_pct']:.2f}%")
        if result["alerts"]:
            for alert in result["alerts"]:
                print(f"       ⚠️  {alert}")
        time.sleep(0.3)  # 模拟采集间隔

    # 服务器状态
    print("\n" + "=" * 60)
    print("📋 服务器健康状态:")
    status = monitor.get_status()
    print(f"  服务器: {status['server']}")
    print(f"  状态:   {status['status']}")
    print(f"  健康度: {status['health_score']}/100")
    print(f"  近1小时告警: {status['recent_alerts']} 条")

    # 告警汇总
    print("\n📢 告警历史:")
    critical_alerts = monitor.get_alert_history("critical")
    warning_alerts = monitor.get_alert_history("warning")
    print(f"  Critical: {len(critical_alerts)} 条")
    print(f"  Warning:  {len(warning_alerts)} 条")

    print("\n✅ 监控演示完成!")


if __name__ == "__main__":
    run_demo()
