# Draw Call 优化案例：诊断、方案取舍与验证

> 本案例用于演示如何把“Draw Call 高、野外卡顿”转为可验证的假设。适用背景为 Unity 2022.3 + URP；不预先认定 CPU 提交或 GPU 工作是瓶颈。

**证据说明（2026-10-16 复核）：** 旧稿将 3200+ → 480 Draw Call、22 → 58 FPS、温度及各步骤收益写成实测结论，但仓库未附原始 Profiler、设备记录、项目资源、构建哈希或固定回放，无法复核。旧稿与 AI 对话中的 GPU Wait、Batches Saved 后值也不一致。这些数字仅保留为历史叙述，撤回其作为已验证性能结果的含义；以下给出修正后的排查与复测流程。

## 背景

问题描述来自一个开放世界 RPG 手游场景：野外分布大量树木、石头和建筑，同时运行战斗血条、小地图与任务 UI。旧稿列出的 iPhone 8、骁龙 845、2km × 2km 区域等信息未附测试工程，只能作为待重建的场景条件。不能凭场景总对象数推断同一帧的可见数量或绘制次数。

适合本流程的条件：能固定路线和镜头，能取得目标机 CPU/GPU 记录，能比较同一画质下的基线与候选构建，并能回滚资源修改。不适合直接照搬：不同 Unity/管线版本、没有 Shader 源码的资源、随时移动的建筑、没有遮挡的空旷地形，以及不能接受画面变化的内容。

## 症状

### 1. 先保存可以比较的数据

保存 Unity/URP 与系统版本、图形 API、设备、构建提交、分辨率、画质、帧率上限、刷新率、路线和温度条件。分别记录启动、稳态战斗、最坏特效镜头及持续运行。Draw Call、SetPass、三角形数是归因线索，不是通用验收阈值。

### 2. 关键发现必须有证据

| 线索 | 旧稿推断的问题 | 应如何验证 |
|------|------|------|
| WaitForPresent 占比高 | 直接认定 GPU 算力瓶颈 | 对齐 CPU/渲染线程与 GPU 时间线，检查垂直同步、限帧和等待 |
| Saved by Batching 较低 | 直接认定合批几乎失效 | 分别检查 SRP Batcher、实例化和静态路径，不能用一个计数覆盖所有机制 |
| SetPass 较高 | 当成材质数量 | 查看 Shader 变体、Pass、相机与阴影；一次切换不是简单的一材质一 SetPass |
| 运行后掉帧发热 | 直接认定特定 CPU 降频比例 | 保存平台热状态、频率及帧时间记录，排除网络、后台任务和环境差异 |

等待标记解释依据 [Unity Profiler 标记](https://docs.unity3d.com/2022.3/Documentation/Manual/profiler-markers.html)。没有 GPU 采样能力时写“缺失”，不能用 Wait 时间补作 GPU 执行时间。

## 排查过程

### 第一步：Frame Debugger 与 CPU/GPU 时间线配合

在可重现帧查看渲染事件及合批中断原因：Mesh、材质槽、Shader 变体、Pass、阴影、灯光、透明排序、Lightmap 和属性块。排序还受渲染队列、深度和管线策略影响，不能只按距离和材质名称推断。

Frame Debugger 用于解释“画了什么”，不能单独给出 Canvas CPU 重建时间或真机 GPU 每个事件的成本。耗时结论回到 Profiler/平台工具验证。

### 第二步：材质审计只读开始

旧稿的 `MergeMaterials` 按 Shader 名和主纹理 InstanceID 分组后直接写回 `sharedMaterials`，会把不同颜色、法线/遮罩贴图、关键字、队列和 Pass 设置误当等价。该自动替换代码已撤下。

改用 [render_audit 只读工具](../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/)：

- 读取 `sharedMaterials`，不用会实例化材质的 `Renderer.material` / `materials`；不写回材质、不修改 Static 和 MPB。
- 依据实际 Mesh/Material 对象身份列出共享引用候选，不以同 Shader、同主纹理或同名判断材质等价。
- 分开报告禁用/未激活、属性块、缺 Mesh、空槽和多子网格情况；运行时 ID 只用于同一次快照，不能跨会话当稳定资源键。
- 即使两个对象共享 Mesh/Material，仍要用 Frame Debugger 核实路径、灯光、阴影、变体和可见性。

编辑 Inspector 或拖入 Prefab 并不自动证明产生了材质副本。应查明资源引用、`Renderer.material` 调用及运行时创建路径，再判断是否可以复用。

### 第三步：检查几何与可见性

LOD 按屏幕相对高度阈值工作，受物体尺寸、摄像机投影/FOV 等影响，不能把任意 30/80 米距离公式当通用设置。对不同视角检查切换、阴影、碰撞分离和过渡；淡入淡出需要对应配置与 Shader 支持。[LOD Group](https://docs.unity3d.com/2022.3/Documentation/Manual/class-LODGroup.html)

视锥剔除与遮挡剔除不同：没有烘焙遮挡不意味着相机背后的物体全被绘制。遮挡可减少视锥内但被遮住的对象，也增加查询和数据成本，需在有遮挡与开阔路线分别开关比较。[遮挡剔除](https://docs.unity3d.com/2022.3/Documentation/Manual/OcclusionCulling.html)

### 第四步：UI 脏标记与重建分开计量

| 操作 | 修正后的解释 | 实作要求 |
|------|------|------|
| 反复 SetActive(true) | 不能按调用次数推导同样次数的 OnEnable 或 Canvas rebuild；实际状态转换才是关键 | 数据/显隐变化时更新，测实际生命周期和重建标记 |
| Image.fillAmount 改变 | 会调用 SetVerticesDirty，不是零重建成本 | Image.Type.Filled，值变化才写，测 Graphic rebuild；不要每帧重复算无变化值 |
| CanvasGroup.alpha = 0 | 隐藏外观不等于禁用脚本/布局，也不自动关闭交互 | 按需求设置 interactable/blocksRaycasts；测隐藏状态负载 |
| 禁用 Canvas 或 GameObject | 两者生命周期、保留状态与重启成本不同 | 按面板生命周期选型，用 Profiler 检查恢复时峰值 |
| 动静 UI 拆分 Canvas | 可隔离变化，也可能增加绘制与管理开销 | 用重建耗时和绘制数一起验收 |

依据 [Unity UI 优化建议](https://unity.com/how-to/unity-ui-optimization-tips) 和 [uGUI Image 源码](https://github.com/Unity-Technologies/uGUI/blob/main/com.unity.ugui/Runtime/UGUI/UI/Core/Image.cs)，项目还需对照实际安装包版本。旧稿中包含未声明 `prefab`、`fillImage` 的池化血条片段已移除；它不能直接编译，也未处理容量、重置和重复归还，不应作为完整实现。

## 根因分析（先写假设，再补结果）

| 假设 | 支持它需要什么 | 可否被证伪 |
|------|------|------|
| CPU 渲染提交过重 | 目标机提交阶段超预算，改变该路径可缩短有效工作时间 | 若 GPU 或逻辑才占主导，降 Draw Call 后总帧时间可能不变 |
| 远景几何/阴影过重 | GPU 记录和可见几何显示相关阶段昂贵 | 只减三角形而像素/带宽仍占主导，则收益有限 |
| UI 高频变化扩大重建 | Timeline 中布局/重建与更新路径可对应 | 并非每次 setter 都重建一次，可能同帧合并 |
| 热稳态负载过高 | 同条件持续运行的功耗/热状态与掉帧记录 | 需排除环境、充电和后台任务，不能只用触感归因 |

本仓库目前不具备将以上假设认定为该产品根因的原始证据，也不分配各项“贡献百分比”。

## 解决方案（按证据排序）

### 1. 材质复用与图集

仅在完整属性、资源生命周期和画面一致性允许时，建立显式资源映射，小范围替换、支持 Undo/回滚并检查 Prefab overrides 与持久化。图集要测试 UV、mipmap、过滤、重复采样和驻留成本；不能根据同名 Shader 自动覆盖材质。

### 2. 按对象选择合批路线

| 路线 | 适用条件 | 不适用或需额外评估 |
|------|------|------|
| SRP Batcher | 兼容 Shader、没有 MPB 的 URP 对象，CPU 状态准备昂贵 | 不保证 Draw Call 变少；变体切换仍需检查 |
| GPU Instancing | 重复 Mesh、同 Material，Shader 与实例属性支持 | Unity 2022.3 的 SRP Batcher 优先；勾 Enable GPU Instancing 并非已合批证据 |
| Static Batching | 静态变换、满足静态批处理约束且内存允许 | 增加几何内存，不能给所有建筑/植被无条件标记；顶点动画需结合实际 Shader/网格约束验证 |

MPB 在 SRP Batcher 中有兼容性代价，也不会自动把 `_BaseColor` 或自定义参数变成实例属性。不要同时“全场标 Static + 写 MPB”当作统一修复。[SRP Batcher](https://docs.unity3d.com/2022.3/Documentation/Manual/SRPBatcher.html)、[GPU Instancing](https://docs.unity3d.com/2022.3/Documentation/Manual/GPUInstancing.html)、[Static Batching](https://docs.unity3d.com/2022.3/Documentation/Manual/static-batching.html)

### 3. LOD、遮挡与 UI

只有瓶颈证据支持才投入制作。逐项开关比较，检查过渡、轮廓、阴影、穿帮、交互及内存；UI 先减少无变化更新，再评估 Canvas 隔离和生命周期。帧时间收益不能从几何比例或重建调用次数直接推算。

## 效果与验证

### 仓库代码验证

只读审计示例的 .NET 回归验证材质对象身份、候选过滤与确定性排序；Unity Editor 回归验证实际 API、材质引用、MPB、Static 标志及场景 dirty 状态不变。详见 [运行方法与验证范围](../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/README.md)。这些检查不运行 URP 真机渲染，不能证明实例化成功或产品 FPS 提升。

### 真机复测记录（待执行）

| 单项改动 | 必须提交的基线/候选证据 | 当前状态 |
|------|------|------|
| 材质复用 | 资源映射、属性与各 Pass 画面对照、提交耗时和显存 | 待验证 |
| SRP/实例化/静态路线 | 实际事件、CPU/GPU 毫秒、几何内存与加载时间 | 待验证 |
| LOD/遮挡 | 同镜头开关对照、GPU 时间、过渡/阴影、剔除 CPU 与烘焙数据 | 待验证 |
| UI | 更新路径、Layout/Graphic/Canvas 时间、交互与恢复峰值 | 待验证 |
| 完整方案 | 最低机型固定路线、帧时间分位数与超预算比例、热稳态、峰值内存 | 待验证 |

每轮保留构建哈希、配置、原始记录和窗口，交替 A/B，多轮观察波动；项目先定义预算与可接受回退量。不得把不同路线的计数拼成同一效果表，也不能把多项合并收益归给某个批处理脚本。完整方法见 [客户端优化：验证方法](../mds/3.研发能力/3.1.3.客户端优化.md#验证方法)。

## 经验教训

- 工具输出需要解释范围：计数、等待与真实工作时间不是同一个指标。
- 资源修改先证明等价并可回滚，只读审计不能越界成自动修复。
- 合批、LOD、遮挡和 UI 拆分都有成本，条件不满足时可以不采用。
- 案例缺证据时保留不确定性；可运行代码测试和真机性能验证分别报告。

## 图谱知识点映射

- [客户端优化](../mds/3.研发能力/3.1.3.客户端优化.md) — 预算、归因、方案边界与验收
- [UI 系统](../mds/3.研发能力/3.1.6.UI系统.md) — 布局、重建与生命周期
- [图形与渲染](../mds/2.技术能力/2.1.1.图形与渲染.md) — Pass、批处理、LOD 与可见性
- [AI 协作复核](../ai-cases/unity-drawcall-optimization.md) — 旧脚本的拒绝原因与安全替代
