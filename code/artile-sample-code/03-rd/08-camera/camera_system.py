"""
游戏摄像机系统 — 跟随/震屏/缩放

对应文章：三-08-摄像机控制
"""

import math
import random
import time
from dataclasses import dataclass


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, o): return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o): return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s): return Vec2(self.x * s, self.y * s)
    def length(self): return math.hypot(self.x, self.y)


class Camera:
    def __init__(self, x=0, y=0, zoom=1.0):
        self.pos = Vec2(x, y)
        self.target = Vec2(x, y)
        self.zoom = zoom
        self.target_zoom = zoom
        self._shake_intensity = 0.0
        self._shake_duration = 0.0
        self._shake_timer = 0.0
        self._bound_min = Vec2(-1000, -1000)
        self._bound_max = Vec2(1000, 1000)
        self.smooth_factor = 0.1
        self.zoom_speed = 0.08

    def follow(self, target_x: float, target_y: float):
        self.target = Vec2(target_x, target_y)

    def update(self, dt: float = 0.016):
        # 平滑跟随 (lerp)
        self.pos.x += (self.target.x - self.pos.x) * self.smooth_factor
        self.pos.y += (self.target.y - self.pos.y) * self.smooth_factor

        # 震屏衰减
        if self._shake_timer > 0:
            self._shake_timer -= dt
            t = max(0, self._shake_timer / self._shake_duration)
            intensity = self._shake_intensity * t
            self.pos.x += random.uniform(-intensity, intensity)
            self.pos.y += random.uniform(-intensity, intensity)

        # 缩放平滑
        self.zoom += (self.target_zoom - self.zoom) * self.zoom_speed

        # 边界限制
        self.pos.x = max(self._bound_min.x, min(self._bound_max.x, self.pos.x))
        self.pos.y = max(self._bound_min.y, min(self._bound_max.y, self.pos.y))

    def shake(self, intensity: float = 10.0, duration: float = 0.3):
        self._shake_intensity = intensity
        self._shake_duration = duration
        self._shake_timer = duration

    def set_zoom(self, zoom: float):
        self.target_zoom = max(0.5, min(3.0, zoom))

    def __repr__(self):
        return (f"Camera(pos=({self.pos.x:.1f}, {self.pos.y:.1f}), "
                f"zoom={self.zoom:.2f}, shake={self._shake_timer:.3f}s)")


def main():
    print("=== 游戏摄像机系统演示 ===\n")

    cam = Camera(smooth_factor=0.3)

    # 演示跟随
    print("[摄像机跟随玩家移动]")
    player_positions = [(0, 0), (50, 0), (100, 50), (150, 80)]
    for px, py in player_positions:
        cam.follow(px, py)
        for _ in range(10):  # 10帧
            cam.update()
        print(f"  玩家({px},{py}) → {cam}")

    # 演示震屏
    print("\n[震屏效果 — 爆炸!]")
    cam.shake(intensity=15, duration=0.5)
    for i in range(30):
        cam.update()
        if i % 10 == 0:
            print(f"  frame {i}: {cam}")

    # 演示缩放
    print("\n[视野缩放]")
    for z in [2.0, 0.8, 1.5, 1.0]:
        cam.set_zoom(z)
        for _ in range(5):
            cam.update()
        print(f"  目标缩放={z} → 当前={cam.zoom:.2f}")

    print("\n✅ 摄像机系统演示完成")


if __name__ == "__main__":
    main()
