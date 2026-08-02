#!/usr/bin/env python3
"""
游戏开发必需数学知识 —— 纯 Python 实现

对应文章：../../游戏开发图谱/基础能力篇/一-04-游戏开发需要哪些数学基础？按场景梳理.md

包含：
  - Vector2 / Vector3 类（加减乘除、归一化、长度）
  - 点积（Dot Product）—— 用于视角判定、光照计算
  - 叉积（Cross Product）—— 用于法线、旋转方向
  - Matrix4x4 变换 —— TRS 矩阵、向量变换
  - 距离计算
  - Lerp / Slerp 插值 —— 平滑过渡、相机跟随
  - AABB 碰撞检测 —— 轴对齐包围盒碰撞
  - 贝塞尔曲线插值 —— 弹道路径、缓动曲线

纯标准库，无外部依赖。
"""

import math


# ═══════════════════════════════════════════════════════════════════════════════
# Vector2
# ═══════════════════════════════════════════════════════════════════════════════

class Vector2:
    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Vector2({self.x:.3f}, {self.y:.3f})"

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> "Vector2":
        return Vector2(-self.x, -self.y)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> "Vector2":
        mag = self.length()
        if mag > 1e-10:
            return self / mag
        return Vector2(0, 0)

    @staticmethod
    def dot(a: "Vector2", b: "Vector2") -> float:
        """点积：a·b = |a||b|cos(θ)。用于视角判定、光照强度。"""
        return a.x * b.x + a.y * b.y

    @staticmethod
    def distance(a: "Vector2", b: "Vector2") -> float:
        return (b - a).length()

    @staticmethod
    def lerp(a: "Vector2", b: "Vector2", t: float) -> "Vector2":
        """线性插值。t=0→a, t=1→b。"""
        t = max(0.0, min(1.0, t))
        return Vector2(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)


# ═══════════════════════════════════════════════════════════════════════════════
# Vector3
# ═══════════════════════════════════════════════════════════════════════════════

class Vector3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self) -> str:
        return f"Vector3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float) -> "Vector3":
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> "Vector3":
        return Vector3(-self.x, -self.y, -self.z)

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> "Vector3":
        mag = self.length()
        if mag > 1e-10:
            return self / mag
        return Vector3(0, 0, 0)

    @staticmethod
    def dot(a: "Vector3", b: "Vector3") -> float:
        """点积。dot > 0 → 夹角 < 90°（面向）；dot = 0 → 垂直；dot < 0 → 背向。"""
        return a.x * b.x + a.y * b.y + a.z * b.z

    @staticmethod
    def cross(a: "Vector3", b: "Vector3") -> "Vector3":
        """叉积。结果垂直于 a 和 b 所在平面，右手定则。用于法线、力矩。"""
        return Vector3(
            a.y * b.z - a.z * b.y,
            a.z * b.x - a.x * b.z,
            a.x * b.y - a.y * b.x,
        )

    @staticmethod
    def distance(a: "Vector3", b: "Vector3") -> float:
        return (b - a).length()

    @staticmethod
    def lerp(a: "Vector3", b: "Vector3", t: float) -> "Vector3":
        """线性插值。"""
        t = max(0.0, min(1.0, t))
        return Vector3(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            a.z + (b.z - a.z) * t,
        )

    @staticmethod
    def slerp(a: "Vector3", b: "Vector3", t: float) -> "Vector3":
        """球面线性插值。用于方向/旋转平滑过渡，避免角速度不匀。"""
        t = max(0.0, min(1.0, t))
        a_n = a.normalized()
        b_n = b.normalized()
        dot = Vector3.dot(a_n, b_n)
        dot = max(-1.0, min(1.0, dot))

        theta = math.acos(dot)  # 夹角
        if theta < 1e-10:
            return b_n  # 几乎重合，直接返回

        sin_theta = math.sin(theta)
        wa = math.sin((1.0 - t) * theta) / sin_theta
        wb = math.sin(t * theta) / sin_theta
        return Vector3(
            wa * a_n.x + wb * b_n.x,
            wa * a_n.y + wb * b_n.y,
            wa * a_n.z + wb * b_n.z,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Matrix4x4（列主序，与 OpenGL / Unity 一致）
# ═══════════════════════════════════════════════════════════════════════════════

class Matrix4x4:
    """
    4x4 变换矩阵，列主序存储。
    索引: m[col][row], 即 m00=第一列第一行, m10=第二列第一行...

    布局 (col-major flat):
      [m00, m10, m20, m30,  m01, m11, m21, m31,
       m02, m12, m22, m32,  m03, m13, m23, m33]
    """

    def __init__(self):
        # 初始化为单位矩阵
        self.m = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]

    def __repr__(self) -> str:
        lines = []
        for row in range(4):
            vals = [f"{self.m[col * 4 + row]:8.3f}" for col in range(4)]
            lines.append("  [" + ", ".join(vals) + "]")
        return "Matrix4x4(\n" + "\n".join(lines) + "\n)"

    @staticmethod
    def translate(tx: float, ty: float, tz: float) -> "Matrix4x4":
        m = Matrix4x4()
        m.m[3 * 4 + 0] = tx  # m03
        m.m[3 * 4 + 1] = ty  # m13
        m.m[3 * 4 + 2] = tz  # m23
        return m

    @staticmethod
    def scale(sx: float, sy: float, sz: float) -> "Matrix4x4":
        m = Matrix4x4()
        m.m[0 * 4 + 0] = sx
        m.m[1 * 4 + 1] = sy
        m.m[2 * 4 + 2] = sz
        return m

    @staticmethod
    def rotate_z(angle_rad: float) -> "Matrix4x4":
        """绕 Z 轴旋转（2D 游戏常用）"""
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        m = Matrix4x4()
        m.m[0 * 4 + 0] = c
        m.m[0 * 4 + 1] = s
        m.m[1 * 4 + 0] = -s
        m.m[1 * 4 + 1] = c
        return m

    @staticmethod
    def trs(tx: float, ty: float, tz: float,
            angle_rad: float,
            sx: float, sy: float, sz: float) -> "Matrix4x4":
        """组合 TRS 变换：先缩放、再旋转、再平移。"""
        t_mat = Matrix4x4.translate(tx, ty, tz)
        r_mat = Matrix4x4.rotate_z(angle_rad)
        s_mat = Matrix4x4.scale(sx, sy, sz)
        # M = T * R * S
        return multiply(t_mat, multiply(r_mat, s_mat))

    def transform_point(self, v: Vector3) -> Vector3:
        """变换点 (w=1)。"""
        x = v.x * self.m[0] + v.y * self.m[4] + v.z * self.m[8] + self.m[12]
        y = v.x * self.m[1] + v.y * self.m[5] + v.z * self.m[9] + self.m[13]
        z = v.x * self.m[2] + v.y * self.m[6] + v.z * self.m[10] + self.m[14]
        w = v.x * self.m[3] + v.y * self.m[7] + v.z * self.m[11] + self.m[15]
        if abs(w) > 1e-10:
            return Vector3(x / w, y / w, z / w)
        return Vector3(x, y, z)

    def transform_direction(self, v: Vector3) -> Vector3:
        """变换方向 (w=0)，不受平移影响。"""
        x = v.x * self.m[0] + v.y * self.m[4] + v.z * self.m[8]
        y = v.x * self.m[1] + v.y * self.m[5] + v.z * self.m[9]
        z = v.x * self.m[2] + v.y * self.m[6] + v.z * self.m[10]
        return Vector3(x, y, z)


def multiply(a: Matrix4x4, b: Matrix4x4) -> Matrix4x4:
    """矩阵乘法。"""
    result = Matrix4x4()
    for col in range(4):
        for row in range(4):
            total = 0.0
            for k in range(4):
                total += a.m[k * 4 + row] * b.m[col * 4 + k]
            result.m[col * 4 + row] = total
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# AABB 碰撞检测
# ═══════════════════════════════════════════════════════════════════════════════

class AABB:
    """轴对齐包围盒。min 为左下后角，max 为右上前角。"""

    __slots__ = ("min", "max")

    def __init__(self, min_point: Vector3, max_point: Vector3):
        self.min = min_point
        self.max = max_point

    def __repr__(self) -> str:
        return f"AABB(min={self.min}, max={self.max})"

    def intersects(self, other: "AABB") -> bool:
        """判断两个 AABB 是否相交（SAT 分离轴定理的特例）。"""
        return (
            self.min.x <= other.max.x and self.max.x >= other.min.x and
            self.min.y <= other.max.y and self.max.y >= other.min.y and
            self.min.z <= other.max.z and self.max.z >= other.min.z
        )

    def contains_point(self, point: Vector3) -> bool:
        return (
            self.min.x <= point.x <= self.max.x and
            self.min.y <= point.y <= self.max.y and
            self.min.z <= point.z <= self.max.z
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 贝塞尔曲线
# ═══════════════════════════════════════════════════════════════════════════════

def cubic_bezier(
    p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float
) -> Vector3:
    """三次贝塞尔曲线。p0=起点, p1/p2=控制点, p3=终点, t∈[0,1]。

    常用于弹道路径、缓动曲线、过场相机路径。
    """
    t = max(0.0, min(1.0, t))
    u = 1.0 - t
    # B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3
    return Vector3(
        u**3 * p0.x + 3 * u**2 * t * p1.x + 3 * u * t**2 * p2.x + t**3 * p3.x,
        u**3 * p0.y + 3 * u**2 * t * p1.y + 3 * u * t**2 * p2.y + t**3 * p3.y,
        u**3 * p0.z + 3 * u**2 * t * p1.z + 3 * u * t**2 * p2.z + t**3 * p3.z,
    )


def quadratic_bezier(
    p0: Vector3, p1: Vector3, p2: Vector3, t: float
) -> Vector3:
    """二次贝塞尔曲线。简化版，适合抛物线弹道。"""
    t = max(0.0, min(1.0, t))
    u = 1.0 - t
    return Vector3(
        u**2 * p0.x + 2 * u * t * p1.x + t**2 * p2.x,
        u**2 * p0.y + 2 * u * t * p1.y + t**2 * p2.y,
        u**2 * p0.z + 2 * u * t * p1.z + t**2 * p2.z,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Main 演示
# ═══════════════════════════════════════════════════════════════════════════════

def demo_vectors():
    print("─" * 60)
    print("  1. Vector3 基本运算 & 点积/叉积")
    print("─" * 60)

    player_pos = Vector3(0, 0, 0)
    enemy_pos  = Vector3(5, 0, 3)
    player_fwd = Vector3(0, 1, 0)    # 玩家面朝 +Y

    to_enemy = (enemy_pos - player_pos).normalized()
    dot_val = Vector3.dot(player_fwd, to_enemy)
    dist = Vector3.distance(player_pos, enemy_pos)

    print(f"  玩家位置: {player_pos}")
    print(f"  敌人位置: {enemy_pos}")
    print(f"  朝向敌人方向: {to_enemy}")
    print(f"  距离: {dist:.3f} 单位")
    print(f"  dot(前方向, 敌人方向) = {dot_val:.3f}")
    if dot_val > 0.7:
        print("  → 敌人正在前方视野内 ✓")
    elif dot_val > 0:
        print("  → 敌人在前方，偏侧")
    else:
        print("  → 敌人在背后！")

    # 叉积：计算向上方向与敌人方向的旋转轴
    world_up = Vector3(0, 0, 1)
    cross_val = Vector3.cross(player_fwd, to_enemy)
    print(f"  cross(前方向, 敌人方向) = {cross_val}  (旋转轴)")


def demo_transforms():
    print("\n" + "─" * 60)
    print("  2. Matrix4x4 TRS 变换")
    print("─" * 60)

    # 一个精灵：位于 (3, 2)，旋转 45°，缩放 1.5x
    trs = Matrix4x4.trs(tx=3.0, ty=2.0, tz=0.0,
                        angle_rad=math.radians(45),
                        sx=1.5, sy=1.5, sz=1.0)
    print("  TRS 矩阵:")
    print(trs)

    local_point = Vector3(1, 0, 0)  # 模型空间中的点
    world_point = trs.transform_point(local_point)
    print(f"  模型空间点 {local_point} → 世界空间 {world_point}")


def demo_aabb():
    print("\n" + "─" * 60)
    print("  3. AABB 碰撞检测")
    print("─" * 60)

    box1 = AABB(Vector3(0, 0, 0), Vector3(2, 2, 2))
    box2 = AABB(Vector3(1, 1, 1), Vector3(3, 3, 3))  # 相交
    box3 = AABB(Vector3(3, 0, 0), Vector3(5, 2, 2))  # 不相交

    print(f"  box1: {box1}")
    print(f"  box2: {box2}")
    print(f"  box3: {box3}")
    print(f"  box1 ∩ box2: {box1.intersects(box2)}  ← 应该为 True ✓")
    print(f"  box1 ∩ box3: {box1.intersects(box3)}  ← 应该为 False ✓")


def demo_bezier():
    print("\n" + "─" * 60)
    print("  4. 贝塞尔曲线 — 弹道路径")
    print("─" * 60)

    # 抛物线弹道：起点=炮口，终点=目标，控制点=弹道顶点
    start = Vector3(0, 0, 0)         # 炮口
    end   = Vector3(10, 0, 0)        # 目标
    apex  = Vector3(5, 4, 0)         # 弹道顶点

    print(f"  起点 (炮口):  {start}")
    print(f"  终点 (目标):  {end}")
    print(f"  控制点(顶点): {apex}")
    print()
    print(f"  {'t':>6}  {'位置'}")
    print(f"  {'─' * 6}  {'─' * 30}")

    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        pt = quadratic_bezier(start, apex, end, t)
        print(f"  {t:>6.2f}  {pt}")


def demo_lerp_slerp():
    print("\n" + "─" * 60)
    print("  5. Lerp / Slerp 插值对比")
    print("─" * 60)

    a = Vector3(1, 0, 0)
    b = Vector3(0, 1, 0)
    print(f"  a = {a}")
    print(f"  b = {b}")
    print(f"\n  {'t':>6}  {'Lerp':>20}  {'Slerp':>20}  {'|Lerp|':>8}  {'|Slerp|':>8}")
    print(f"  {'─'*6}  {'─'*20}  {'─'*20}  {'─'*8}  {'─'*8}")

    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        lerp_v  = Vector3.lerp(a, b, t)
        slerp_v = Vector3.slerp(a, b, t)
        print(f"  {t:>6.2f}  {str(lerp_v):>20}  {str(slerp_v):>20}  "
              f"{lerp_v.length():>8.3f}  {slerp_v.length():>8.3f}")
    print()
    print("  注意: Lerp 在中间点长度变短（角速度不匀）,")
    print("        Slerp 始终保持单位长度（匀速旋转）。")


def main():
    print("=" * 60)
    print("  游戏开发必需数学知识 — Demo")
    print("=" * 60)
    print()

    demo_vectors()
    demo_transforms()
    demo_aabb()
    demo_bezier()
    demo_lerp_slerp()

    print("\n" + "=" * 60)
    print("  完成 ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
