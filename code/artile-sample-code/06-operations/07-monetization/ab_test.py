"""
A/B 测试框架

对应文章：六-07-商业化设计
"""

import random
from dataclasses import dataclass
from typing import List


@dataclass
class Variant:
    name: str
    impressions: int = 0
    conversions: int = 0

    @property
    def rate(self) -> float:
        return self.conversions / self.impressions if self.impressions > 0 else 0.0


class ABTest:
    def __init__(self, name: str):
        self.name = name
        self.variants: List[Variant] = []

    def add_variant(self, name: str):
        self.variants.append(Variant(name))

    def assign(self, user_id: int) -> Variant:
        idx = user_id % len(self.variants)
        v = self.variants[idx]
        v.impressions += 1
        return v

    def convert(self, variant: Variant):
        variant.conversions += 1

    def report(self):
        print(f"\n📊 A/B 测试 [{self.name}] 报告:")
        print(f"{'变体':<12} {'展示':<8} {'转化':<8} {'转化率':<8} {'提升':<8}")
        base_rate = self.variants[0].rate if self.variants else 0
        for v in self.variants:
            lift = (v.rate / base_rate - 1) * 100 if base_rate > 0 else 0
            print(f"{v.name:<12} {v.impressions:<8} {v.conversions:<8} "
                  f"{v.rate:.1%}     {lift:+.1f}%")


def main():
    print("=== A/B 测试框架演示 ===\n")

    test = ABTest("商城按钮颜色测试")
    test.add_variant("红色按钮(控制组)")
    test.add_variant("蓝色按钮")
    test.add_variant("金色按钮")

    print("[模拟 1000 次展示]")
    for uid in range(1000):
        v = test.assign(uid)
        # 不同变体有不同的转化率
        rates = {"红色按钮(控制组)": 0.05, "蓝色按钮": 0.07, "金色按钮": 0.09}
        if random.random() < rates[v.name]:
            test.convert(v)

    test.report()
    print("\n✅ A/B 测试演示完成")


if __name__ == "__main__":
    main()
