#!/usr/bin/env python3
"""
开发工具箱 — 资源依赖检查器 + 日志解析器 + 性能计时器

纯标准库实现，模拟游戏开发工具链核心：
1. 资源依赖检查器 — 检测循环依赖和缺失引用
2. 日志解析器 — 结构化解析游戏运行日志
3. 性能计时器 — 帧耗时追踪 + 各子系统耗时分解

运行：python dev_tools.py
"""

import os
import re
import time
import json
import fnmatch
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ══════════════════════════════════════════════
# 1. 资源依赖检查器
# ══════════════════════════════════════════════

@dataclass
class ResourceNode:
    """资源节点"""
    path: str
    deps: List[str] = field(default_factory=list)        # 直接依赖
    referenced_by: List[str] = field(default_factory=list)  # 被谁引用
    exists: bool = True


class DependencyChecker:
    """资源依赖图分析器

    检测：
    - 循环依赖 (A→B→C→A)
    - 缺失资源 (引用不存在的文件)
    - 孤立资源 (没有被任何资源引用)
    """

    def __init__(self):
        self.nodes: Dict[str, ResourceNode] = {}

    def add_resource(self, path: str, dependencies: List[str]):
        """注册资源及其依赖"""
        if path not in self.nodes:
            self.nodes[path] = ResourceNode(path=path)
        node = self.nodes[path]
        node.deps = dependencies

        # 建立反向引用
        for dep in dependencies:
            if dep not in self.nodes:
                self.nodes[dep] = ResourceNode(path=dep)
            self.nodes[dep].referenced_by.append(path)

    def mark_missing(self, path: str):
        """标记资源为缺失（如磁盘上不存在）"""
        if path not in self.nodes:
            self.nodes[path] = ResourceNode(path=path, exists=False)
        else:
            self.nodes[path].exists = False

    def find_circular_deps(self) -> List[List[str]]:
        """DFS 检测循环依赖，返回所有循环路径"""
        cycles = []
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {k: WHITE for k in self.nodes}
        parent: Dict[str, Optional[str]] = {}

        def dfs(u: str):
            color[u] = GRAY
            for v in self.nodes[u].deps:
                if v not in self.nodes:
                    continue
                if color.get(v) == GRAY:
                    # 找到循环：回溯构建路径
                    cycle = [v, u]
                    p = parent.get(u)
                    while p is not None and p != v:
                        cycle.append(p)
                        p = parent.get(p)
                    cycle.append(v)
                    cycle.reverse()
                    cycles.append(cycle)
                elif color.get(v) == WHITE:
                    parent[v] = u
                    dfs(v)
            color[u] = BLACK

        for node in self.nodes:
            if color.get(node) == WHITE:
                dfs(node)

        return cycles

    def find_missing_refs(self) -> List[Tuple[str, str]]:
        """检测缺失依赖（引用了不存在的资源）"""
        missing = []
        for path, node in self.nodes.items():
            if not node.exists:
                continue
            for dep in node.deps:
                if dep not in self.nodes:
                    missing.append((path, dep))
                elif not self.nodes[dep].exists:
                    missing.append((path, dep))
        return missing

    def find_orphans(self) -> List[str]:
        """检测孤立资源（没有被任何存在的资源引用）"""
        orphans = []
        for path, node in self.nodes.items():
            if not node.exists:
                continue
            if not node.referenced_by:
                orphans.append(path)
            else:
                # 所有引用者都不存在 → 也是孤儿
                all_refs_missing = all(
                    ref not in self.nodes or not self.nodes[ref].exists
                    for ref in node.referenced_by
                )
                if all_refs_missing:
                    orphans.append(path)
        return orphans

    def summary(self) -> str:
        """生成依赖分析报告"""
        total = len(self.nodes)
        missing = sum(1 for n in self.nodes.values() if not n.exists)
        circular = self.find_circular_deps()
        missing_refs = self.find_missing_refs()
        orphans = self.find_orphans()

        lines = [
            f"资源总数: {total} (存在: {total - missing}, 缺失: {missing})",
            f"循环依赖: {len(circular)} 个",
            f"缺失引用: {len(missing_refs)} 个",
            f"孤立资源: {len(orphans)} 个",
        ]

        if circular:
            lines.append("\n⚠️  循环依赖:")
            for cycle in circular:
                lines.append(f"  {' → '.join(cycle)}")

        if missing_refs:
            lines.append("\n❌ 缺失引用:")
            for src, dep in missing_refs:
                lines.append(f"  {src} → {dep} (不存在)")

        if orphans:
            lines.append("\n👻 孤立资源:")
            for o in orphans:
                lines.append(f"  {o}")

        return "\n".join(lines)


def demo_dependency_checker():
    """演示依赖检查"""
    print("═══ 1. 资源依赖检查器 ═══")

    checker = DependencyChecker()

    # 模拟一个游戏项目的资源依赖
    resources = {
        "textures/player.png": ["shaders/player.shader", "materials/player.mat"],
        "materials/player.mat": ["textures/player.png", "shaders/player.shader"],
        "shaders/player.shader": ["includes/common.glsl"],
        "includes/common.glsl": [],
        "textures/enemy.png": ["shaders/enemy.shader"],     # enemy.shader 缺失！
        "scenes/level1.json": ["textures/player.png", "textures/enemy.png", "audio/bgm.ogg"],
        "audio/bgm.ogg": [],
        "prefabs/sword.prefab": ["prefabs/sword.prefab"],   # 自引用循环！
        "textures/unused.png": [],                           # 孤立资源
    }

    for path, deps in resources.items():
        checker.add_resource(path, deps)

    # 标记缺失
    checker.mark_missing("shaders/enemy.shader")

    print()
    print(checker.summary())
    print()


# ══════════════════════════════════════════════
# 2. 日志解析器
# ══════════════════════════════════════════════

@dataclass
class LogEntry:
    """结构化日志条目"""
    timestamp: str = ""
    level: str = "INFO"
    module: str = ""
    message: str = ""
    raw: str = ""
    extra: dict = field(default_factory=dict)


class LogParser:
    """游戏日志解析器

    支持格式：[2024-01-15 14:32:10] [ERROR] [Physics] Collision spike detected
    输出：结构化 LogEntry + 聚合统计
    """

    # 日志正则
    _LOG_PATTERN = re.compile(
        r'\[(?P<ts>[^\]]+)\]\s*'
        r'\[(?P<level>DEBUG|INFO|WARN|ERROR|FATAL)\]\s*'
        r'\[(?P<module>[^\]]+)\]\s*'
        r'(?P<message>.+)'
    )

    @classmethod
    def parse_line(cls, line: str) -> Optional[LogEntry]:
        """解析单行日志"""
        m = cls._LOG_PATTERN.match(line.strip())
        if not m:
            return None
        return LogEntry(
            timestamp=m.group("ts"),
            level=m.group("level"),
            module=m.group("module"),
            message=m.group("message").strip(),
            raw=line.strip(),
        )

    @classmethod
    def parse_multi(cls, text: str) -> List[LogEntry]:
        """解析多行日志"""
        entries = []
        for line in text.splitlines():
            entry = cls.parse_line(line)
            if entry:
                entries.append(entry)
        return entries

    @staticmethod
    def aggregate(entries: List[LogEntry]) -> dict:
        """聚合统计"""
        stats = {
            "total": len(entries),
            "by_level": defaultdict(int),
            "by_module": defaultdict(int),
            "errors": [],
            "warnings": [],
        }
        for e in entries:
            stats["by_level"][e.level] += 1
            stats["by_module"][e.module] += 1
            if e.level == "ERROR":
                stats["errors"].append(e)
            elif e.level == "WARN":
                stats["warnings"].append(e)
        return stats

    @staticmethod
    def filter_by(entries: List[LogEntry],
                  level: Optional[str] = None,
                  module: Optional[str] = None,
                  keyword: Optional[str] = None) -> List[LogEntry]:
        """过滤日志"""
        result = entries
        if level:
            result = [e for e in result if e.level == level.upper()]
        if module:
            result = [e for e in result if e.module == module]
        if keyword:
            result = [e for e in result if keyword.lower() in e.message.lower()]
        return result


# 模拟日志数据
SAMPLE_LOGS = """
[2024-01-15 14:32:01] [INFO] [Engine] Game initialization started
[2024-01-15 14:32:01] [INFO] [Renderer] OpenGL 4.6 context created
[2024-01-15 14:32:02] [WARN] [Resource] Texture 'brick.png' not found, using fallback
[2024-01-15 14:32:03] [INFO] [Audio] Audio device opened: 48000Hz stereo
[2024-01-15 14:32:05] [ERROR] [Physics] NaN detected in transform matrix for entity #42
[2024-01-15 14:32:05] [ERROR] [Physics] Collision solver overflow: 512 contacts exceeded
[2024-01-15 14:32:06] [WARN] [Network] High latency detected: 340ms (threshold: 200ms)
[2024-01-15 14:32:07] [INFO] [Script] Lua VM initialized, 245 scripts loaded
[2024-01-15 14:32:08] [ERROR] [Script] Runtime error: attempt to index nil value (entity.lua:127)
[2024-01-15 14:32:10] [INFO] [Engine] Game loop started at 60 FPS
[2024-01-15 14:32:15] [WARN] [Memory] GC triggered: heap 128MB → 96MB, took 3.2ms
[2024-01-15 14:32:20] [INFO] [Engine] Shutdown initiated
[2024-01-15 14:32:21] [INFO] [Engine] Shutdown complete
"""


def demo_log_parser():
    """演示日志解析"""
    print("═══ 2. 日志解析器 ═══")

    entries = LogParser.parse_multi(SAMPLE_LOGS)
    stats = LogParser.aggregate(entries)

    print(f"  解析了 {stats['total']} 条日志\n")

    # 按级别统计
    print("  日志级别分布:")
    for level in ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]:
        count = stats["by_level"].get(level, 0)
        if count:
            bar = "█" * count
            print(f"    {level:<6}: {count:>2} {bar}")

    # 按模块统计
    print("\n  模块分布:")
    for mod, count in sorted(stats["by_module"].items()):
        print(f"    {mod:<12}: {count:>2}")

    # 错误详情
    if stats["errors"]:
        print(f"\n  ❌ 错误 ({len(stats['errors'])} 条):")
        for e in stats["errors"]:
            print(f"    [{e.timestamp}] [{e.module}] {e.message}")

    # 过滤示例
    print("\n  🔍 过滤示例 — Physics 模块日志:")
    physics_logs = LogParser.filter_by(entries, module="Physics")
    for e in physics_logs:
        print(f"    [{e.level}] {e.message}")
    print()


# ══════════════════════════════════════════════
# 3. 性能计时器
# ══════════════════════════════════════════════

@dataclass
class FrameMetrics:
    """单帧性能指标"""
    frame_id: int
    total_ms: float
    subsystems: Dict[str, float]  # 各子系统耗时(ms)
    fps: float = 0.0


class PerformanceTimer:
    """游戏性能计时器

    功能：
    - 帧耗时追踪（FPS 计算）
    - 各子系统耗时分解（渲染/物理/AI/音频）
    - 滑动窗口统计（平均值、P99）
    """

    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.frame_history: deque = deque(maxlen=window_size)
        self.frame_id: int = 0
        self.subsystem_timers: Dict[str, float] = {}  # 当前帧未完成计时
        self._timer_starts: Dict[str, float] = {}
        self._frame_start: float = 0.0

    def begin_frame(self):
        """开始新帧"""
        self.frame_id += 1
        self._frame_start = time.perf_counter()
        self.subsystem_timers = {}
        self._timer_starts = {}

    def begin(self, name: str):
        """开始计时某个子系统"""
        self._timer_starts[name] = time.perf_counter()

    def end(self, name: str):
        """结束计时某个子系统"""
        if name not in self._timer_starts:
            return
        elapsed = (time.perf_counter() - self._timer_starts[name]) * 1000.0  # ms
        self.subsystem_timers[name] = elapsed
        del self._timer_starts[name]

    def end_frame(self) -> FrameMetrics:
        """结束当前帧"""
        total_ms = (time.perf_counter() - self._frame_start) * 1000.0
        # 未结束的计时器自动结算
        for name in list(self._timer_starts.keys()):
            self.end(name)

        fps = 1000.0 / total_ms if total_ms > 0 else 0.0

        metrics = FrameMetrics(
            frame_id=self.frame_id,
            total_ms=total_ms,
            subsystems=dict(self.subsystem_timers),
            fps=fps,
        )
        self.frame_history.append(metrics)
        return metrics

    def stats(self) -> dict:
        """计算滑动窗口统计"""
        if not self.frame_history:
            return {}

        totals = [f.total_ms for f in self.frame_history]
        totals.sort()

        avg = sum(totals) / len(totals)
        p50 = totals[len(totals) // 2]
        p99 = totals[int(len(totals) * 0.99)]
        p99_9 = totals[min(int(len(totals) * 0.999), len(totals) - 1)]
        min_val = totals[0]
        max_val = totals[-1]

        # 各子系统平均耗时
        subs_avg = defaultdict(float)
        subs_count = defaultdict(int)
        for f in self.frame_history:
            for name, ms in f.subsystems.items():
                subs_avg[name] += ms
                subs_count[name] += 1
        for name in subs_avg:
            subs_avg[name] /= subs_count[name]

        return {
            "frames": len(totals),
            "avg_ms": avg,
            "min_ms": min_val,
            "max_ms": max_val,
            "p50_ms": p50,
            "p99_ms": p99,
            "p99_9_ms": p99_9,
            "avg_fps": 1000.0 / avg if avg > 0 else 0,
            "subsystems_avg": dict(subs_avg),
        }

    def format_stats(self) -> str:
        """格式化输出统计"""
        s = self.stats()
        if not s:
            return "  (无数据)"

        lines = [
            f"  采样帧数: {s['frames']}",
            f"  平均帧时: {s['avg_ms']:.2f} ms → {s['avg_fps']:.1f} FPS",
            f"  最小/最大: {s['min_ms']:.2f} / {s['max_ms']:.2f} ms",
            f"  P50/P99/P99.9: {s['p50_ms']:.2f} / {s['p99_ms']:.2f} / {s['p99_9_ms']:.2f} ms",
        ]
        if s["subsystems_avg"]:
            lines.append("  子系统耗时分解:")
            total_sub = sum(s["subsystems_avg"].values())
            for name, ms in sorted(s["subsystems_avg"].items(), key=lambda x: -x[1]):
                pct = (ms / total_sub * 100) if total_sub > 0 else 0
                bar_len = int(pct / 5)
                bar = "█" * bar_len
                lines.append(f"    {name:<14}: {ms:6.2f} ms ({pct:5.1f}%) {bar}")
        return "\n".join(lines)


def demo_performance_timer():
    """演示性能计时器"""
    print("═══ 3. 性能计时器 ═══")

    timer = PerformanceTimer(window_size=30)

    # 模拟 30 帧的游戏运行
    print("  模拟 30 帧 (每帧含 5 个子系统)...\n")

    for _ in range(30):
        timer.begin_frame()

        # 模拟各子系统耗时
        subsystems = [
            ("Render",  3.0 + abs(__import__("random").gauss(0, 0.5))),
            ("Physics", 4.0 + abs(__import__("random").gauss(0, 1.0))),
            ("AI",      2.5 + abs(__import__("random").gauss(0, 0.8))),
            ("Audio",   0.5 + abs(__import__("random").gauss(0, 0.1))),
            ("Script",  1.0 + abs(__import__("random").gauss(0, 0.3))),
        ]

        for name, base_ms in subsystems:
            timer.begin(name)
            # 模拟实际耗时
            time.sleep(base_ms / 15000.0)  # 缩放到极短时间
            timer.end(name)

        metrics = timer.end_frame()

    # 输出统计
    print(timer.format_stats())
    print()


# ══════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  开发工具箱 — 依赖检查 | 日志解析 | 性能计时")
    print("=" * 60)
    print()

    demo_dependency_checker()
    demo_log_parser()
    demo_performance_timer()

    print("=" * 60)
    print("  演示完成！")
    print("  核心：DFS循环检测 → 日志正则解析 → 滑动窗口FPS统计")
    print("=" * 60)


if __name__ == "__main__":
    main()
