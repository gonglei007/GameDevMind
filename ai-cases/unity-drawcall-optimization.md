# 用 Cursor 优化 Unity 开放世界 Draw Call

> 这是一份 AI 建议复核记录：从“看计数列方案”转为“明确假设、只读审计、逐项验证”。AI 生成脚本同样需要检查渲染路径、场景修改范围和边界条件。

**复核说明（2026-10-16）：** 仓库没有旧稿所述 Profiler 截图、原始完整会话、Unity 工程或真机记录；下文保留的是旧稿的提示词与输出摘录，不能证明对话逐字完整，也不能证明提速数字。旧稿“API 准确、边界合理”的评价已撤回。历史输出用于说明错误，不应复制执行。

## 背景

旧稿描述 Unity 2022 LTS + URP 开放世界手游，在 iPhone 8 上出现 Draw Call 3200+、22 FPS 和 WaitForPresent 占比 40%。这些是未复核的历史输入。Wait 占比本身不能确定 GPU 算力瓶颈，先补帧限制、CPU/渲染线程/GPU 时间线、构建配置和固定路线。[Unity Profiler 标记](https://docs.unity3d.com/2022.3/Documentation/Manual/profiler-markers.html)

## 对话记录

### 第一轮：贴 Profiler，Cursor 给方向

旧稿用户提示词摘录：

> 这个 Unity 场景 Draw Call 3200+，帧率只有 22fps。
> GPU WaitForPresent 占 40%。帮我分析原因并给出优化方案。

旧输出建议合并同 Shader 材质、检查 Static、植被实例化和 LOD，并把 Batches Saved 较少解释为合批失效。

**人工复核：不接受直接结论。** 同 Shader 不代表材质等价；Saved by Batching 不能覆盖 SRP Batcher 的 CPU 状态优化；Wait 可能涉及垂直同步。先补齐测量条件，再决定哪个阶段值得优化，不能由单张计数截图推导根因。

### 第二轮：追问 Static 标记

旧稿用户提示词摘录：

> 为什么静态物体没有合批？场景里 200 栋建筑理论上都是静态的，
> Batches Saved 却只有 ~200。

旧输出要求检查 `Batching Static`，旧稿随后声称有 160 栋标记不完整。

**人工复核：作为待验证假设保留。** 仓库没有对象清单或抓帧证明该数量；静态变换、管线兼容性、几何内存和实际渲染路径仍需核实。检查标记只是排查步骤，不能因此认定静态批处理是唯一或最佳路线。

### 第三轮：批量修复脚本的错误

旧稿请求同时设置 `BatchingStatic` 和 MPB，以便 GPU Instancing。以下保留旧脚本中的核心原样片段，**仅作反例，不可作为修复方案**：

```csharp
var flags = GameObjectUtility.GetStaticEditorFlags(r.gameObject);
flags |= StaticEditorFlags.BatchingStatic;
GameObjectUtility.SetStaticEditorFlags(r.gameObject, flags);

// 设置 MaterialPropertyBlock 用于 GPU Instancing
var mpb = new MaterialPropertyBlock();
r.GetPropertyBlock(mpb);
r.SetPropertyBlock(mpb);
```

拒绝原因：

- Static Batching、SRP Batcher 和 GPU Instancing 是需选择和验证的路线。Unity 2022.3 中 SRP Batcher 优先，MPB 还会使 Renderer 退出 SRP Batcher；不能把两类改动当统一提速操作。
- 读回再原样写 MPB 没有定义任何实例属性，不能使任意 Shader 变成支持实例化。旧输出未检查 Mesh、材质槽、Shader 或对象生命周期。
- 旧脚本没有 Undo、场景持久化/Prefab override 设计，也没有预览与回滚报告。进度条不解决这些正确性问题。

原理依据 [SRP Batcher](https://docs.unity3d.com/2022.3/Documentation/Manual/SRPBatcher.html) 与 [GPU Instancing](https://docs.unity3d.com/2022.3/Documentation/Manual/GPUInstancing.html)。

## 修正后的协作流程

新的提示词：

> Unity 2022.3 + URP。请先列出缺失的测量条件，再生成只读审计工具。
> 读取已加载普通场景的 MeshRenderer，包括未激活对象，但分别标明其状态。
> 依据实际 Mesh/Material 引用统计单子网格共享候选；MPB、空槽、缺 Mesh 等单独报告。
> 不使用 Renderer.material，不替换 sharedMaterials，不改 Static 或 MPB。
> 不声称候选必然合批。给出不改场景的集成回归和真机 A/B 验证步骤。

实际替代实现：[render_audit](../code/gamedevmind/3.研发能力/3.1.3.客户端优化/render_audit/)。独立核心可以在 .NET CI 中运行；Unity Editor 适配器读取场景，集成回归检查真实对象引用、属性块、Static 标志与场景 dirty 状态。该工具只生成诊断信息，不做资源修复或性能测量。

若后续需要批量修改，先提供明确对象清单、允许改变的属性、视觉对照、Undo/持久化与回滚方案，再实现，不能把“审计”悄悄扩大为“全场修复”。

## 最终成果与证据边界

| 项目 | 可以确认的交付 | 尚不能确认 |
|------|------|------|
| 知识纠错 | 撤回 Wait、合批计数及 MPB/Static 的错误解释 | 该产品真实瓶颈与各步骤收益 |
| 代码 | 替换为只读审计，附核心与 Editor 回归入口 | 所有 Shader/管线的兼容性或真实实例化路径 |
| 性能 | 提供 [案例复测表](../cases/drawcall-optimization.md#效果与验证) | 历史 3200 → 480、22 → 58 FPS 及温度提升 |

旧稿效果表中的 GPU Wait/Batches Saved 后值与配套案例不同，且缺少统一采样口径，因此不继续当作验证结果传播。仓库测试通过只证明列明的代码行为；产品性能仍需目标设备、固定路线、同画质多轮 A/B 与原始记录。

## 关键收获

1. 诊断需要能证伪的假设和原始记录，不能把 AI 给出的可能性写成已定位根因。
2. 工具代码要核实副作用和 API 语义；先只读列清单，再决定是否实施修改。
3. 代码正确性、渲染路径和真机收益分别验证；没有测到的结果明确标为待验证。

## 图谱知识点映射

- [客户端优化](../mds/3.研发能力/3.1.3.客户端优化.md) — 预算、取舍与验收
- [客户端3D场景开发](../mds/3.研发能力/3.1.2.客户端3D场景开发.md) — 可见性与 LOD
- [C#语言](../mds/1.基础能力/1.1.3.C%23语言.md) — 工具边界和回归
- [Draw Call 诊断案例](../cases/drawcall-optimization.md) — 材质、UI 纠错与待执行复测
