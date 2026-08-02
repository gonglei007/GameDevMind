#!/usr/bin/env python3
"""
图形渲染管线模拟 — MVP 顶点变换 + Phong 光照 + ASCII 输出

纯标准库实现，模拟 GPU 渲染管线核心步骤：
1. 顶点着色器：模型→世界→视图→裁剪空间 (MVP 矩阵变换)
2. 光栅化：三角形扫描线填充
3. 片段着色器：Phong 光照模型 (环境光 + 漫反射 + 镜面高光)
4. 输出：ASCII 字符画渲染结果

运行：python shader_demo.py
"""

import math
import sys

# ──────────────────────────────────────────────
# 向量与矩阵运算 (纯 Python)
# ──────────────────────────────────────────────


def vec3(x=0.0, y=0.0, z=0.0):
    return [x, y, z]


def vec3_add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def vec3_sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def vec3_mul(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def vec3_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec3_cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def vec3_normalize(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-8:
        return [0.0, 0.0, 0.0]
    return [v[0] / length, v[1] / length, v[2] / length]


def mat4_identity():
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def mat4_mul(a, b):
    """4x4 矩阵乘法"""
    result = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            result[i][j] = sum(a[i][k] * b[k][j] for k in range(4))
    return result


def mat4_mul_vec4(m, v):
    """矩阵乘 vec4，返回 vec4"""
    return [
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2] + m[0][3] * v[3],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2] + m[1][3] * v[3],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2] + m[2][3] * v[3],
        m[3][0] * v[0] + m[3][1] * v[1] + m[3][2] * v[2] + m[3][3] * v[3],
    ]


def mat4_translate(x, y, z):
    m = mat4_identity()
    m[0][3] = x
    m[1][3] = y
    m[2][3] = z
    return m


def mat4_scale(sx, sy, sz):
    m = mat4_identity()
    m[0][0] = sx
    m[1][1] = sy
    m[2][2] = sz
    return m


def mat4_rotate_y(angle):
    """绕 Y 轴旋转"""
    c = math.cos(angle)
    s = math.sin(angle)
    m = mat4_identity()
    m[0][0] = c
    m[0][2] = s
    m[2][0] = -s
    m[2][2] = c
    return m


def mat4_rotate_x(angle):
    """绕 X 轴旋转"""
    c = math.cos(angle)
    s = math.sin(angle)
    m = mat4_identity()
    m[1][1] = c
    m[1][2] = -s
    m[2][1] = s
    m[2][2] = c
    return m


def mat4_perspective(fov_y, aspect, near, far):
    """透视投影矩阵"""
    f = 1.0 / math.tan(fov_y / 2.0)
    m = [[0.0] * 4 for _ in range(4)]
    m[0][0] = f / aspect
    m[1][1] = f
    m[2][2] = (far + near) / (near - far)
    m[2][3] = (2.0 * far * near) / (near - far)
    m[3][2] = -1.0
    return m


# ──────────────────────────────────────────────
# 顶点与三角形定义
# ──────────────────────────────────────────────


class Vertex:
    """顶点：位置 + 法线"""

    def __init__(self, position, normal):
        self.position = list(position)
        self.normal = list(normal)
        self.clip_pos = None  # 变换后的裁剪坐标


class Triangle:
    """三角形面"""

    def __init__(self, v0, v1, v2):
        self.vertices = [v0, v1, v2]


def create_cube(center, size):
    """创建立方体的顶点和三角形"""
    h = size / 2.0
    cx, cy, cz = center

    # 8 个顶点 (位置) — 每个面有独立法线，所以需要 24 个顶点
    verts = []
    tris = []

    def add_face(p0, p1, p2, p3, normal):
        i = len(verts)
        verts.append(Vertex(p0, normal))
        verts.append(Vertex(p1, normal))
        verts.append(Vertex(p2, normal))
        verts.append(Vertex(p3, normal))
        tris.append(Triangle(verts[i], verts[i + 1], verts[i + 2]))
        tris.append(Triangle(verts[i], verts[i + 2], verts[i + 3]))

    # 前面 (z+)
    add_face(
        [cx - h, cy - h, cz + h],
        [cx + h, cy - h, cz + h],
        [cx + h, cy + h, cz + h],
        [cx - h, cy + h, cz + h],
        [0, 0, 1],
    )
    # 后面 (z-)
    add_face(
        [cx + h, cy - h, cz - h],
        [cx - h, cy - h, cz - h],
        [cx - h, cy + h, cz - h],
        [cx + h, cy + h, cz - h],
        [0, 0, -1],
    )
    # 右面 (x+)
    add_face(
        [cx + h, cy - h, cz + h],
        [cx + h, cy - h, cz - h],
        [cx + h, cy + h, cz - h],
        [cx + h, cy + h, cz + h],
        [1, 0, 0],
    )
    # 左面 (x-)
    add_face(
        [cx - h, cy - h, cz - h],
        [cx - h, cy - h, cz + h],
        [cx - h, cy + h, cz + h],
        [cx - h, cy + h, cz - h],
        [-1, 0, 0],
    )
    # 顶面 (y+)
    add_face(
        [cx - h, cy + h, cz + h],
        [cx + h, cy + h, cz + h],
        [cx + h, cy + h, cz - h],
        [cx - h, cy + h, cz - h],
        [0, 1, 0],
    )
    # 底面 (y-)
    add_face(
        [cx - h, cy - h, cz - h],
        [cx + h, cy - h, cz - h],
        [cx + h, cy - h, cz + h],
        [cx - h, cy - h, cz + h],
        [0, -1, 0],
    )

    return verts, tris


# ──────────────────────────────────────────────
# 渲染管线
# ──────────────────────────────────────────────


class RenderPipeline:
    def __init__(self, width=80, height=40):
        self.width = width
        self.height = height
        self.framebuffer = [[0.0] * width for _ in range(height)]
        self.depthbuffer = [[float("inf")] * width for _ in range(height)]

        # 光照参数
        self.ambient = 0.15
        self.light_dir = vec3_normalize([0.5, 1.0, 0.8])
        self.light_color = [1.0, 0.95, 0.8]
        self.object_color = [0.3, 0.6, 0.9]
        self.specular_color = [1.0, 1.0, 1.0]
        self.shininess = 32.0
        self.view_dir = vec3_normalize([0, 0, 1])

    def clear(self):
        self.framebuffer = [[0.0] * self.width for _ in range(self.height)]
        self.depthbuffer = [[float("inf")] * self.width for _ in range(self.height)]

    def vertex_shader(self, vertex, mvp):
        """顶点着色器：MVP 变换 + 法线变换 (用 MVP 的左上 3x3)"""
        pos4 = mat4_mul_vec4(mvp, vertex.position + [1.0])
        # 透视除法
        w = pos4[3]
        if abs(w) < 1e-8:
            w = 1e-8
        ndc = [pos4[0] / w, pos4[1] / w, pos4[2] / w]

        # 屏幕坐标
        screen_x = (ndc[0] + 1.0) * 0.5 * self.width
        screen_y = (1.0 - ndc[1]) * 0.5 * self.height
        vertex.clip_pos = [screen_x, screen_y, ndc[2], w]
        return vertex

    def fragment_shader(self, normal, world_pos):
        """Phong 光照模型"""
        n = vec3_normalize(normal)
        l = self.light_dir

        # 环境光
        ambient = [self.ambient * self.object_color[i] for i in range(3)]

        # 漫反射 (Lambert)
        diff_intensity = max(vec3_dot(n, l), 0.0)
        diffuse = [diff_intensity * self.object_color[i] * self.light_color[i] for i in range(3)]

        # 镜面高光 (Blinn-Phong)
        h = vec3_normalize(vec3_add(l, self.view_dir))
        spec_intensity = max(vec3_dot(n, h), 0.0) ** self.shininess
        specular = [spec_intensity * self.specular_color[i] for i in range(3)]

        color = [
            min(ambient[i] + diffuse[i] + specular[i], 1.0) for i in range(3)
        ]
        return color

    def rasterize_triangle(self, v0, v1, v2):
        """扫描线光栅化 + 透视校正插值"""
        # 按 Y 排序
        pts = sorted(
            [(v0.clip_pos, v0.normal), (v1.clip_pos, v1.normal), (v2.clip_pos, v2.normal)],
            key=lambda x: x[0][1],
        )
        (p0, n0), (p1, n1), (p2, n2) = pts

        x0, y0, z0, w0 = p0
        x1, y1, z1, w1 = p1
        x2, y2, z2, w2 = p2

        # 裁剪
        if y0 >= self.height or y2 < 0:
            return

        def draw_scanline(y, xa, za, wa, na, xb, zb, wb, nb):
            if y < 0 or y >= self.height:
                return
            if xa > xb:
                xa, xb = xb, xa
                za, zb = zb, za
                wa, wb = wb, wa
                na, nb = nb, na

            x_start = max(0, int(xa))
            x_end = min(self.width - 1, int(xb))

            for x in range(x_start, x_end + 1):
                if xa == xb:
                    t = 0.5
                else:
                    t = (x - xa) / (xb - xa)
                # 透视校正插值
                w_recip = 1.0 / (wa + t * (wb - wa)) if abs(wa + t * (wb - wa)) > 1e-8 else 1.0
                z = (za + t * (zb - za)) * w_recip
                # 法线插值
                interp_normal = [
                    na[i] + t * (nb[i] - na[i]) for i in range(3)
                ]

                if z < self.depthbuffer[y][x]:
                    self.depthbuffer[y][x] = z
                    color = self.fragment_shader(interp_normal, None)
                    intensity = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
                    self.framebuffer[y][x] = intensity

        def edge_interp(ya, yb, pa, pb):
            """在 ya 和 yb 之间插值边"""
            dy = yb - ya
            if abs(dy) < 1e-8:
                return []
            result = []
            y_start = max(0, int(ya))
            y_end = min(self.height - 1, int(yb))
            for y in range(y_start, y_end + 1):
                t = (y - ya) / dy
                result.append((
                    y,
                    pa[0] + t * (pb[0] - pa[0]),  # x
                    pa[2] + t * (pb[2] - pa[2]),  # z
                    pa[3] + t * (pb[3] - pa[3]),  # w
                    [pa_n[i] + t * (pb_n[i] - pa_n[i]) for i in range(3)],  # normal
                ))
            return result

        pa_n, pb_n, pc_n = n0, n1, n2

        # 上半部分 (y0→y1)
        if y1 > y0:
            edge_left = edge_interp(y0, y1, p0, p1)
            edge_right = edge_interp(y0, y2, p0, p2)
            # 处理哪边是左
            for (yl, xl, zl, wl, nl), (yr, xr, zr, wr, nr) in zip(edge_left, edge_right):
                if xl < xr:
                    draw_scanline(yl, xl, zl, wl, nl, xr, zr, wr, nr)
                else:
                    draw_scanline(yl, xr, zr, wr, nr, xl, zl, wl, nl)

        # 下半部分 (y1→y2)
        if y2 > y1:
            edge_left = edge_interp(y1, y2, p1, p2)
            edge_right = edge_interp(y0, y2, p0, p2)
            for (yl, xl, zl, wl, nl), (yr, xr, zr, wr, nr) in zip(edge_left, edge_right):
                if xl < xr:
                    draw_scanline(yl, xl, zl, wl, nl, xr, zr, wr, nr)
                else:
                    draw_scanline(yl, xr, zr, wr, nr, xl, zl, wl, nl)

    def render(self, verts, tris, mvp):
        """完整渲染一帧"""
        self.clear()

        # 顶点着色阶段
        for v in verts:
            self.vertex_shader(v, mvp)

        # 光栅化阶段
        for tri in tris:
            self.rasterize_triangle(tri.vertices[0], tri.vertices[1], tri.vertices[2])

    def display(self):
        """ASCII 输出"""
        chars = " .:-=+*#%@"
        lines = []
        for row in self.framebuffer:
            line = ""
            for val in row:
                idx = min(int(val * (len(chars) - 1)), len(chars) - 1)
                line += chars[idx]
            lines.append(line)
        return "\n".join(lines)


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  图形渲染管线模拟 — MVP 变换 + Phong 光照")
    print("  模拟 GPU 顶点着色器 → 光栅化 → 片段着色器流程")
    print("=" * 60)
    print()

    # 创建渲染管线 (80x40 字符画布)
    pipeline = RenderPipeline(80, 40)

    # 创建立方体
    verts, tris = create_cube(center=(0, 0, 0), size=1.5)

    # 构建 MVP 矩阵
    # Model: 旋转
    model = mat4_mul(mat4_rotate_y(math.radians(30)), mat4_rotate_x(math.radians(20)))
    model = mat4_mul(model, mat4_translate(0, 0, -3))

    # View: 世界空间 → 相机空间
    view = mat4_translate(0, 0, 0)  # 相机在原点

    # Projection: 透视投影
    proj = mat4_perspective(math.radians(60), 80.0 / 40.0, 0.1, 100.0)

    # MVP = Projection × View × Model
    mvp = mat4_mul(proj, mat4_mul(view, model))

    print("【MVP 矩阵已构建】")
    print(f"  画布: {pipeline.width}x{pipeline.height} 字符")
    print(f"  光照: 环境光={pipeline.ambient}, 光源方向={pipeline.light_dir}")
    print(f"  物体颜色: {pipeline.object_color}")
    print()

    # 渲染
    pipeline.render(verts, tris, mvp)

    # 输出
    print(pipeline.display())
    print()
    print("─" * 60)
    print("  管线流程: 顶点着色器(MVP变换) → 扫描线光栅化 →")
    print("            Phong光照(环境+漫反射+镜面高光) → ASCII输出")
    print("─" * 60)

    # 交互：让用户尝试不同角度
    print("\n💡 试试不同角度？修改代码中的旋转角度即可。")
    print("   模型旋转: Y轴30° + X轴20°")
    print("   位置: Z=-3 (相机前方3单位)")


if __name__ == "__main__":
    main()
