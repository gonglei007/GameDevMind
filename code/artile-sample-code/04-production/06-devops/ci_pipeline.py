"""
CI/CD 流水线模拟

对应文章：四-06-DevOps 实践
"""

import time
import random
from enum import Enum
from dataclasses import dataclass

class Stage(Enum):
    LINT = "代码检查"
    TEST = "单元测试"
    BUILD = "构建打包"
    DEPLOY = "部署上线"

@dataclass
class PipelineResult:
    stage: Stage
    success: bool
    duration: float
    details: str = ""

class CIPipeline:
    def __init__(self):
        self.results = []
        self._checks = {
            Stage.LINT: lambda: random.random() > 0.05,
            Stage.TEST: lambda: random.random() > 0.10,
            Stage.BUILD: lambda: random.random() > 0.15,
            Stage.DEPLOY: lambda: random.random() > 0.08,
        }

    def run(self):
        print("🚀 启动 CI/CD 流水线")
        for stage in Stage:
            print(f"  ▶ {stage.value}...", end=" ")
            start = time.time()

            try:
                success = self._checks[stage]()
                duration = time.time() - start
                status = "✅" if success else "❌"
                print(f"{status} ({duration:.1f}s)")
                self.results.append(PipelineResult(stage, success, duration))
                if not success:
                    print(f"  ⛔ 流水线在 [{stage.value}] 阶段失败，停止后续步骤")
                    break
            except Exception as e:
                print(f"❌ 异常: {e}")
                self.results.append(PipelineResult(stage, False, 0, str(e)))
                break

    def report(self):
        print("\n📊 流水线报告:")
        total = sum(r.duration for r in self.results)
        for r in self.results:
            icon = "✅" if r.success else "❌"
            print(f"  {icon} {r.stage.value}: {r.duration:.1f}s")
        print(f"  ⏱️ 总耗时: {total:.1f}s")
        all_ok = all(r.success for r in self.results)
        print(f"  {'🎉 全部通过！' if all_ok else '⚠️ 存在失败阶段'}")


def main():
    print("=== CI/CD 流水线演示 ===\n")
    ci = CIPipeline()
    ci.run()
    ci.report()

if __name__ == "__main__":
    main()
