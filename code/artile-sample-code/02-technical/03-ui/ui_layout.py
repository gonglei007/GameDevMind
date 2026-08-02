#!/usr/bin/env python3
"""
UI 布局系统 — 锚点 + 弹性盒子模拟 + 事件冒泡

纯标准库实现，模拟游戏 UI 框架核心：
1. 锚点布局 (Anchor) — 基于父容器比例定位
2. 弹性盒子 (Flexbox) — 主轴/交叉轴对齐、间距分配
3. 事件系统 — 事件冒泡 (Bubbling)、捕获阶段

运行：python ui_layout.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Callable


# ──────────────────────────────────────────────
# 几何基础
# ──────────────────────────────────────────────


class Rect:
    """矩形区域"""
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x=0.0, y=0.0, w=0.0, h=0.0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __repr__(self):
        return f"Rect(x={self.x:.0f}, y={self.y:.0f}, w={self.w:.0f}, h={self.h:.0f})"


# ──────────────────────────────────────────────
# 锚点系统
# ──────────────────────────────────────────────


class AnchorPreset(Enum):
    """预设锚点"""
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    MIDDLE_LEFT = "middle-left"
    MIDDLE_CENTER = "middle-center"
    MIDDLE_RIGHT = "middle-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"
    STRETCH = "stretch"


@dataclass
class Anchor:
    """锚点配置 (归一化坐标 0~1)"""
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0

    @classmethod
    def from_preset(cls, preset: AnchorPreset) -> "Anchor":
        mapping = {
            AnchorPreset.TOP_LEFT: (0, 1, 0, 1),
            AnchorPreset.TOP_CENTER: (0.5, 1, 0.5, 1),
            AnchorPreset.TOP_RIGHT: (1, 1, 1, 1),
            AnchorPreset.MIDDLE_LEFT: (0, 0.5, 0, 0.5),
            AnchorPreset.MIDDLE_CENTER: (0.5, 0.5, 0.5, 0.5),
            AnchorPreset.MIDDLE_RIGHT: (1, 0.5, 1, 0.5),
            AnchorPreset.BOTTOM_LEFT: (0, 0, 0, 0),
            AnchorPreset.BOTTOM_CENTER: (0.5, 0, 0.5, 0),
            AnchorPreset.BOTTOM_RIGHT: (1, 0, 1, 0),
            AnchorPreset.STRETCH: (0, 0, 1, 1),
        }
        mx, my, Mx, My = mapping[preset]
        return cls(mx, my, Mx, My)


# ──────────────────────────────────────────────
# Flexbox 布局
# ──────────────────────────────────────────────


class FlexDirection(Enum):
    ROW = "row"
    COLUMN = "column"


class JustifyContent(Enum):
    FLEX_START = "flex-start"
    CENTER = "center"
    FLEX_END = "flex-end"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"


class AlignItems(Enum):
    FLEX_START = "flex-start"
    CENTER = "center"
    FLEX_END = "flex-end"
    STRETCH = "stretch"


@dataclass
class FlexLayout:
    """弹性盒子布局计算器"""
    direction: FlexDirection = FlexDirection.ROW
    justify: JustifyContent = JustifyContent.FLEX_START
    align: AlignItems = AlignItems.CENTER
    gap: float = 4.0
    padding: float = 8.0

    def compute(self, container_rect: Rect, child_sizes: List[tuple]) -> List[Rect]:
        """
        计算子元素位置
        child_sizes: [(width, height), ...] 每个子元素的期望尺寸
        返回: 每个子元素的最终 Rect
        """
        if not child_sizes:
            return []

        is_row = self.direction == FlexDirection.ROW
        main_size = container_rect.w if is_row else container_rect.h
        cross_size = container_rect.h if is_row else container_rect.w

        # 主轴可用空间
        total_child_main = sum(
            cs[0] if is_row else cs[1] for cs in child_sizes
        )
        total_gap = self.gap * (len(child_sizes) - 1)
        available = main_size - self.padding * 2 - total_child_main - total_gap

        # 主轴起始位置和间距
        if self.justify == JustifyContent.FLEX_START:
            main_start = self.padding
            main_gap = self.gap
        elif self.justify == JustifyContent.CENTER:
            main_start = self.padding + available / 2
            main_gap = self.gap
        elif self.justify == JustifyContent.FLEX_END:
            main_start = self.padding + available
            main_gap = self.gap
        elif self.justify == JustifyContent.SPACE_BETWEEN:
            main_start = self.padding
            main_gap = self.gap + available / max(len(child_sizes) - 1, 1)
        elif self.justify == JustifyContent.SPACE_AROUND:
            space = available / len(child_sizes)
            main_start = self.padding + space / 2
            main_gap = self.gap + space
        else:
            main_start = self.padding
            main_gap = self.gap

        results = []
        current_main = main_start

        for cw, ch in child_sizes:
            # 交叉轴对齐
            child_cross = ch if is_row else cw

            if self.align == AlignItems.FLEX_START:
                cross_pos = self.padding
            elif self.align == AlignItems.CENTER:
                cross_pos = self.padding + (cross_size - self.padding * 2 - child_cross) / 2
            elif self.align == AlignItems.FLEX_END:
                cross_pos = cross_size - self.padding - child_cross
            elif self.align == AlignItems.STRETCH:
                child_cross = cross_size - self.padding * 2
                cross_pos = self.padding
                if is_row:
                    ch = child_cross
                else:
                    cw = child_cross
            else:
                cross_pos = self.padding

            if is_row:
                rect = Rect(
                    container_rect.x + current_main,
                    container_rect.y + cross_pos,
                    cw,
                    ch,
                )
            else:
                rect = Rect(
                    container_rect.x + cross_pos,
                    container_rect.y + current_main,
                    cw,
                    ch,
                )

            results.append(rect)
            current_main += (cw if is_row else ch) + main_gap

        return results


# ──────────────────────────────────────────────
# 事件系统 (冒泡)
# ──────────────────────────────────────────────


class EventPhase(Enum):
    CAPTURING = 1   # 从根到目标
    AT_TARGET = 2   # 在目标上
    BUBBLING = 3    # 从目标到根


@dataclass
class UIEvent:
    """UI 事件"""
    type: str
    target: "UIElement" = None
    phase: EventPhase = EventPhase.AT_TARGET
    data: dict = field(default_factory=dict)
    stopped: bool = False

    def stop_propagation(self):
        self.stopped = True


class UIElement:
    """UI 元素 — 支持层级、锚点、事件"""
    _next_id = 0

    def __init__(self, name: str = "", parent: "UIElement" = None):
        self.id = UIElement._next_id
        UIElement._next_id += 1
        self.name = name or f"element_{self.id}"
        self.parent: Optional["UIElement"] = parent
        self.children: List["UIElement"] = []

        # 布局
        self.rect = Rect()
        self.anchor = Anchor()
        self.margin = (0, 0, 0, 0)  # top, right, bottom, left

        # 事件监听
        self.listeners: dict[str, List[Callable]] = {}

        if parent:
            parent.add_child(self)

    def add_child(self, child: "UIElement"):
        child.parent = self
        self.children.append(child)

    def on(self, event_type: str, handler: Callable):
        """注册事件监听"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def dispatch_event(self, event: UIEvent):
        """触发事件 (含冒泡)"""
        # 构建祖先链
        ancestors = []
        node = self
        while node:
            ancestors.append(node)
            node = node.parent

        # 捕获阶段 (从根到目标父级)
        event.phase = EventPhase.CAPTURING
        for node in reversed(ancestors[1:]):  # 跳过自身
            if event.stopped:
                return
            self._fire(node, event)

        # 目标阶段
        event.phase = EventPhase.AT_TARGET
        event.target = self
        if not event.stopped:
            self._fire(self, event)

        # 冒泡阶段 (从父级到根)
        event.phase = EventPhase.BUBBLING
        for node in ancestors[1:]:
            if event.stopped:
                return
            self._fire(node, event)

    def _fire(self, element: "UIElement", event: UIEvent):
        handlers = element.listeners.get(event.type, [])
        for h in handlers:
            h(event)
            if event.stopped:
                return

    def __repr__(self):
        return f"UIElement({self.name}, id={self.id})"


# ──────────────────────────────────────────────
# 可视化
# ──────────────────────────────────────────────


def visualize_tree(root: UIElement, indent: int = 0) -> str:
    """递归可视化 UI 树"""
    lines = []
    prefix = "  " * indent + ("├─ " if indent > 0 else "")
    lines.append(f"{prefix}{root.name} [{root.rect}]")
    for child in root.children:
        lines.append(visualize_tree(child, indent + 1))
    return "\n".join(lines)


def draw_layout(canvas_w: int, canvas_h: int, root: UIElement) -> str:
    """ASCII 绘制布局"""
    grid = [[" "] * canvas_w for _ in range(canvas_h)]

    def draw_rect(rect: Rect, char: str = "█", label: str = ""):
        x0 = max(0, int(rect.x))
        y0 = max(0, int(rect.y))
        x1 = min(canvas_w - 1, int(rect.x + rect.w))
        y1 = min(canvas_h - 1, int(rect.y + rect.h))

        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if y == y0 or y == y1 or x == x0 or x == x1:
                    grid[y][x] = char
        # 标签
        if label and y0 < canvas_h and x0 < canvas_w:
            for i, ch in enumerate(label):
                if x0 + 1 + i < canvas_w - 1:
                    grid[y0][x0 + 1 + i] = ch

    def traverse(node: UIElement):
        if node.rect.w > 0:
            draw_rect(node.rect, char="▓" if node.children else "░", label=node.name[:8])
        for child in node.children:
            traverse(child)

    traverse(root)
    return "\n".join("".join(row) for row in grid)


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  UI 布局系统 — 锚点 + 弹性盒子 + 事件冒泡")
    print("=" * 60)
    print()

    # ── 演示 1: 锚点布局 ──
    print("【演示 1】锚点系统 (Anchor)")
    print("─" * 40)

    screen = UIElement("Screen")
    screen.rect = Rect(0, 0, 80, 30)

    # 创建不同锚点的子元素
    anchors_demo = {
        "TopLeft": AnchorPreset.TOP_LEFT,
        "TopCenter": AnchorPreset.TOP_CENTER,
        "TopRight": AnchorPreset.TOP_RIGHT,
        "MidLeft": AnchorPreset.MIDDLE_LEFT,
        "Center": AnchorPreset.MIDDLE_CENTER,
        "MidRight": AnchorPreset.MIDDLE_RIGHT,
        "BotLeft": AnchorPreset.BOTTOM_LEFT,
        "BotCenter": AnchorPreset.BOTTOM_CENTER,
        "BotRight": AnchorPreset.BOTTOM_RIGHT,
    }

    for name, preset in anchors_demo.items():
        el = UIElement(name, screen)
        el.anchor = Anchor.from_preset(preset)
        a = el.anchor

        # 计算实际像素位置 (从锚点 offset)
        size = 6
        el.rect = Rect(
            a.min_x * (screen.rect.w - size),
            a.min_y * (screen.rect.h - size),
            size,
            3,
        )

    print(draw_layout(80, 30, screen))
    print()

    # ── 演示 2: Flexbox 布局 ──
    print("【演示 2】弹性盒子 (Flexbox)")
    print("─" * 40)

    flex_screen = UIElement("FlexScreen")
    flex_screen.rect = Rect(0, 0, 60, 12)

    # Row 布局
    row_container = UIElement("RowContainer", flex_screen)
    row_container.rect = Rect(2, 2, 56, 4)

    flex = FlexLayout(
        direction=FlexDirection.ROW,
        justify=JustifyContent.SPACE_AROUND,
        align=AlignItems.CENTER,
        gap=2,
        padding=1,
    )

    child_sizes = [(8, 2), (12, 2), (6, 2), (10, 2)]
    child_names = ["BtnA", "BtnLong", "BtnC", "BtnD"]
    positions = flex.compute(row_container.rect, child_sizes)
    for pos, name in zip(positions, child_names):
        el = UIElement(name, row_container)
        el.rect = pos

    # Column 布局
    col_container = UIElement("ColContainer", flex_screen)
    col_container.rect = Rect(2, 7, 15, 4)

    flex_col = FlexLayout(
        direction=FlexDirection.COLUMN,
        justify=JustifyContent.SPACE_BETWEEN,
        align=AlignItems.STRETCH,
        gap=0,
        padding=1,
    )
    col_sizes = [(13, 1), (13, 1), (13, 1)]
    col_names = ["Item1", "Item2", "Item3"]
    col_positions = flex_col.compute(col_container.rect, col_sizes)
    for pos, name in zip(col_positions, col_names):
        el = UIElement(name, col_container)
        el.rect = pos

    print(draw_layout(60, 12, flex_screen))
    print()

    # ── 演示 3: 事件冒泡 ──
    print("【演示 3】事件冒泡 (Event Bubbling)")
    print("─" * 40)

    root = UIElement("Root")
    panel = UIElement("Panel", root)
    button = UIElement("Button", panel)
    label = UIElement("Label", button)

    # 注册事件监听
    def make_handler(name):
        def handler(event: UIEvent):
            phase_names = {EventPhase.CAPTURING: "捕获", EventPhase.AT_TARGET: "目标", EventPhase.BUBBLING: "冒泡"}
            print(f"  [{phase_names[event.phase]}] {name} 收到 '{event.type}' 事件")
            if event.data.get("stop_at") == name:
                event.stop_propagation()
                print(f"    ⛔ {name} 停止冒泡！")
        return handler

    for el in [root, panel, button, label]:
        el.on("click", make_handler(el.name))

    print("  场景: Root > Panel > Button > Label")
    print()

    # 点击 Label — 完整冒泡
    print("  ① 点击 Label (完整冒泡):")
    evt = UIEvent(type="click")
    label.dispatch_event(evt)

    print()
    # 点击 Button — 在 Panel 停止冒泡
    print("  ② 点击 Button (Panel 停止冒泡):")
    evt = UIEvent(type="click", data={"stop_at": "Panel"})
    button.dispatch_event(evt)

    print()
    print("=" * 60)
    print("  演示完成！")
    print("  锚点系统: 9 种预设锚点定位")
    print("  Flexbox: Row/Column + 5 种对齐方式")
    print("  事件系统: 捕获 → 目标 → 冒泡 三阶段")
    print("=" * 60)


if __name__ == "__main__":
    main()
