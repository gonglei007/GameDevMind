# 01-graphics — 图形渲染管线模拟

> 对应文章：二-01 图形渲染

> 正文已瘦身：软件渲染管线完整实现见 `shader_demo.py`，文章保留 Mermaid 与阶段说明。

## 运行

```bash
python shader_demo.py
```

纯标准库，无需安装任何依赖。

## 功能

- **顶点着色器**：MVP 矩阵变换（模型→世界→视图→裁剪空间），支持平移/旋转/缩放/透视投影
- **光栅化**：三角形扫描线填充 + 深度测试 + 透视校正插值
- **片段着色器**：Phong 光照模型（环境光 + Lambert 漫反射 + Blinn-Phong 镜面高光）
- **输出**：80×40 字符 ASCII 画，亮度映射到 ` .:-=+*#%@` 字符集

## 核心概念

| 阶段 | 对应 GPU 管线 | 实现 |
|------|--------------|------|
| 顶点着色器 | Vertex Shader | `vertex_shader()` — MVP 变换 + 透视除法 |
| 图元装配 | Primitive Assembly | 三角形三顶点 → 屏幕坐标 |
| 光栅化 | Rasterizer | `rasterize_triangle()` — 扫描线 + 深度缓冲 |
| 片段着色器 | Fragment Shader | `fragment_shader()` — Phong 光照计算 |
| 输出合并 | Output Merger | 帧缓冲写入 + ASCII 显示 |

## 可调参数

在 `RenderPipeline.__init__()` 和 `main()` 中可调整：
- `width/height`：画布大小
- `ambient`：环境光强度
- `light_dir`：光源方向
- `shininess`：高光锐度
- 模型旋转角度（`mat4_rotate_y`/`mat4_rotate_x`）
- 相机距离（`mat4_translate` 的 Z 分量）
