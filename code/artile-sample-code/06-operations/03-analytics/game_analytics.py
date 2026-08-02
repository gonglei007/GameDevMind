#!/usr/bin/env python3
"""
游戏数据分析 - DAU/留存率/LTV 模拟计算
文章: 06-operations/03-analytics (游戏数据分析)
纯标准库，python3 直接运行
"""

import random
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict


@dataclass
class DailyMetrics:
    """每日指标"""
    date: str
    new_users: int = 0         # 新增用户
    dau: int = 0               # 日活跃用户
    revenue: float = 0.0       # 日收入
    sessions: int = 0          # 会话数
    avg_session_minutes: float = 0.0  # 平均会话时长
    paying_users: int = 0      # 付费用户数
    first_pay_users: int = 0   # 首充用户数


class GameAnalytics:
    """游戏数据分析引擎"""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.daily_metrics: List[DailyMetrics] = []
        # 用户注册日期追踪: user_id -> 注册日期
        self.user_registry: Dict[int, str] = {}
        # 每日登录记录: date -> set of user_ids
        self.daily_logins: Dict[str, set] = defaultdict(set)
        # 付费记录: user_id -> [(date, amount), ...]
        self.payments: Dict[int, List[Tuple[str, float]]] = defaultdict(list)

    def simulate_days(self, days: int = 30,
                      base_new_users: int = 1000,
                      growth_rate: float = 0.02):
        """模拟多日数据"""
        start_date = datetime(2025, 1, 1)
        active_user_pool = set()

        for d in range(days):
            date = (start_date + timedelta(days=d)).strftime("%Y-%m-%d")
            day_of_week = (start_date + timedelta(days=d)).weekday()

            # 新增用户（周末更多）
            weekend_boost = 1.3 if day_of_week >= 5 else 1.0
            new_users = int(base_new_users * (1 + growth_rate) ** d * weekend_boost)
            new_users += random.randint(-50, 50)  # 随机波动

            # 注册新用户
            new_user_ids = list(range(
                max(self.user_registry.keys()) + 1 if self.user_registry else 1,
                max(self.user_registry.keys()) + 1 + new_users if self.user_registry else new_users + 1
            ))
            for uid in new_user_ids:
                self.user_registry[uid] = date
            active_user_pool.update(new_user_ids)

            # 模拟活跃用户登录
            # 已有用户按留存概率登录
            logged_in_today = set(new_user_ids)  # 新用户当天必登录
            for uid in active_user_pool - set(new_user_ids):
                reg_date = datetime.strptime(self.user_registry[uid], "%Y-%m-%d")
                days_since_reg = (start_date + timedelta(days=d) - reg_date).days
                if days_since_reg <= 0:
                    continue
                # 留存概率随天数衰减
                retention_prob = self._retention_probability(days_since_reg)
                if random.random() < retention_prob:
                    logged_in_today.add(uid)

            self.daily_logins[date] = logged_in_today

            # 模拟付费
            daily_revenue = 0.0
            paying_today = 0
            first_pay_today = 0
            for uid in logged_in_today:
                if random.random() < 0.05:  # 5% 付费率
                    # 付费金额 (对数正态分布)
                    amount = round(random.lognormvariate(3.0, 1.0), 2)
                    is_first = len(self.payments[uid]) == 0
                    self.payments[uid].append((date, amount))
                    daily_revenue += amount
                    paying_today += 1
                    if is_first:
                        first_pay_today += 1

            # 记录每日指标
            metrics = DailyMetrics(
                date=date,
                new_users=new_users,
                dau=len(logged_in_today),
                revenue=round(daily_revenue, 2),
                sessions=len(logged_in_today) * random.randint(1, 3),
                avg_session_minutes=round(random.gauss(25, 10), 1),
                paying_users=paying_today,
                first_pay_users=first_pay_today,
            )
            self.daily_metrics.append(metrics)

    @staticmethod
    def _retention_probability(days_since_reg: int) -> float:
        """留存概率函数: D1~40%, D7~15%, D30~5%"""
        return max(0.01, 0.45 * math.exp(-0.1 * days_since_reg))

    def calculate_retention(self, day_n: int = 1) -> Dict[int, float]:
        """计算N日留存率 (按注册批次)"""
        results = {}
        for d, metrics in enumerate(self.daily_metrics):
            reg_date = metrics.date
            target_date_dt = datetime.strptime(reg_date, "%Y-%m-%d") + timedelta(days=day_n)
            target_date = target_date_dt.strftime("%Y-%m-%d")

            if target_date not in self.daily_logins:
                continue

            # 这一天注册的用户
            reg_users = {uid for uid, date in self.user_registry.items()
                         if date == reg_date}
            if not reg_users:
                continue

            # 目标日仍在登录的
            retained = reg_users & self.daily_logins[target_date]
            results[d] = len(retained) / len(reg_users) if reg_users else 0

        return results

    def calculate_dau(self) -> Dict:
        """DAU分析"""
        dau_list = [m.dau for m in self.daily_metrics]
        return {
            "avg_dau": round(sum(dau_list) / len(dau_list), 1) if dau_list else 0,
            "max_dau": max(dau_list) if dau_list else 0,
            "min_dau": min(dau_list) if dau_list else 0,
            "latest_dau": dau_list[-1] if dau_list else 0,
            "trend": "上升" if len(dau_list) >= 2 and dau_list[-1] > dau_list[0]
            else "下降" if len(dau_list) >= 2 and dau_list[-1] < dau_list[0]
            else "平稳",
            "daily": dau_list,
        }

    def calculate_ltv(self, cohort_days: int = 30) -> Dict:
        """计算LTV (用户生命周期价值) — 按注册批次"""
        ltv_by_cohort = {}
        for d, metrics in enumerate(self.daily_metrics):
            reg_date = metrics.date
            reg_users = {uid for uid, date in self.user_registry.items()
                         if date == reg_date}
            if not reg_users:
                continue

            total_revenue = 0.0
            for uid in reg_users:
                for pay_date, amount in self.payments[uid]:
                    total_revenue += amount

            ltv = total_revenue / len(reg_users)
            ltv_by_cohort[reg_date] = round(ltv, 2)

        all_ltv = list(ltv_by_cohort.values())
        return {
            "by_cohort": ltv_by_cohort,
            "avg_ltv": round(sum(all_ltv) / len(all_ltv), 2) if all_ltv else 0,
            "latest_ltv": all_ltv[-1] if all_ltv else 0,
        }

    def calculate_arpu_arppu(self) -> Dict:
        """计算 ARPU 和 ARPPU"""
        total_revenue = sum(m.revenue for m in self.daily_metrics)
        total_dau = sum(m.dau for m in self.daily_metrics)
        total_paying = sum(m.paying_users for m in self.daily_metrics)

        arpu = total_revenue / total_dau if total_dau > 0 else 0
        arppu = total_revenue / total_paying if total_paying > 0 else 0

        return {
            "total_revenue": round(total_revenue, 2),
            "arpu": round(arpu, 2),
            "arppu": round(arppu, 2),
            "pay_rate": f"{total_paying / total_dau * 100:.1f}%" if total_dau > 0 else "0%",
        }

    def report(self) -> str:
        """生成完整分析报告"""
        dau = self.calculate_dau()
        ltv = self.calculate_ltv()
        arpu_arppu = self.calculate_arpu_arppu()
        d7_retention = self.calculate_retention(7)

        lines = ["=" * 60]
        lines.append("  📊 游戏数据分析报告")
        lines.append("=" * 60)

        # DAU
        lines.append(f"\n📈 日活跃用户 (DAU):")
        lines.append(f"  平均: {dau['avg_dau']:.0f}  |  最高: {dau['max_dau']}  |  最低: {dau['min_dau']}")
        lines.append(f"  趋势: {dau['trend']}  |  最新: {dau['latest_dau']}")

        # 留存
        lines.append(f"\n📅 7日留存率 (按注册批次):")
        for batch, rate in list(d7_retention.items())[:5]:
            date = self.daily_metrics[batch].date if batch < len(self.daily_metrics) else f"batch_{batch}"
            lines.append(f"  {date}: {rate*100:.1f}%")
        avg_d7 = sum(d7_retention.values()) / len(d7_retention) if d7_retention else 0
        lines.append(f"  平均 D7 留存: {avg_d7*100:.1f}%")

        # LTV
        lines.append(f"\n💰 用户生命周期价值 (LTV):")
        lines.append(f"  平均 LTV: ¥{ltv['avg_ltv']}")
        lines.append(f"  最新 LTV: ¥{ltv['latest_ltv']}")

        # ARPU / ARPPU
        lines.append(f"\n💳 收入指标:")
        lines.append(f"  总收入: ¥{arpu_arppu['total_revenue']:,.2f}")
        lines.append(f"  ARPU (每用户): ¥{arpu_arppu['arpu']}")
        lines.append(f"  ARPPU (每付费用户): ¥{arpu_arppu['arppu']}")
        lines.append(f"  付费率: {arpu_arppu['pay_rate']}")

        # 付费分布
        lines.append(f"\n📊 付费分布 (最近7天):")
        recent_paying = []
        recent_dates = {m.date for m in self.daily_metrics[-7:]}
        for uid, pays in self.payments.items():
            for pay_date, amount in pays:
                if pay_date in recent_dates:
                    recent_paying.append(amount)
        if recent_paying:
            recent_paying.sort()
            lines.append(f"  总付费人次: {len(recent_paying)}")
            lines.append(f"  中位付费: ¥{recent_paying[len(recent_paying)//2]:.2f}")
            lines.append(f"  最高付费: ¥{recent_paying[-1]:.2f}")
            lines.append(f"  最低付费: ¥{recent_paying[0]:.2f}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  游戏数据分析系统 - 演示")
    print("=" * 60)

    analytics = GameAnalytics(seed=123)
    print("\n🔄 模拟 30 天数据...")
    analytics.simulate_days(days=30, base_new_users=800, growth_rate=0.03)

    # 打印每日数据摘要
    print("\n📋 每日数据摘要 (显示前7天):")
    print(f"{'日期':>12} {'新增':>6} {'DAU':>6} {'收入':>10} {'付费':>5}")
    print("-" * 44)
    for m in analytics.daily_metrics[:7]:
        print(f"{m.date} {m.new_users:>6} {m.dau:>6} ¥{m.revenue:>8,.2f} {m.paying_users:>5}")

    print(f"\n... (共 {len(analytics.daily_metrics)} 天)")

    # 完整报告
    print("\n" + analytics.report())

    print("\n✅ 数据分析演示完成!")


if __name__ == "__main__":
    run_demo()
