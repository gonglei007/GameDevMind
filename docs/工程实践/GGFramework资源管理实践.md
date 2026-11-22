# GGFramework 资源管理实践：加载来源与释放责任

本篇从“资源从哪里来、谁在持有、什么时候可以释放”三个问题出发，先运行 Demo 的资源页，再对照独立 GGResource 的加载器、缓存和异步接口。原理入口见[客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)，版本更新与回滚见[产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md)。

**项目关系与复核：** GGFramework 由本知识库作者维护；本文是工程参考。2026-11-20 完成固定源码核对与 Unity 实跑，实际结果及未覆盖项见[本轮运行记录](GGFrameworkUnity验证记录.md)。共用的[适用环境](GGFramework.md#适用条件)、[源码基线](GGFramework.md#固定源码基线)和[证据分层](GGFramework.md#验证方法与证据边界)由导读统一维护。

## 适用条件

- 具备 C#、Unity 资产与实例、协程和 AssetBundle 基础，需要理解资源共享、加载失败与页面退出时的责任。
- 切换目标平台后，按导读的准备流程重新构建示例 Bundle；区分源码配置、模拟资产与平台 Bundle。
- 先使用示例配置资源，不对生产资产直接执行销毁或强制清理。本文不提供已验收的远程热更新发布链路。

| 核对对象 | 固定提交与依赖 | 本篇使用的实现 |
|---|---|---|
| 独立 GGResource | [14c7a68](https://github.com/gonglei007/GGFramework-GGResource/tree/14c7a685b2b75686e5585f852d1bab93f5f46195)，工程固定 Core `v0.1.1` | `ResourceSystem`、`ResourceObject`、`GBundleBuilder` 与内存态 EditMode 测试 |
| 集成 Demo | [e2a7586](https://github.com/gonglei007/GGFramework-Demo/tree/e2a7586a1325fc8dd762b55d1105de81b9825154)，固定 Core `v0.3.0` | Demo 自有资源源码副本、体验大厅与冒烟测试 |

两边的 `Retain` / `DestroyObject` / `ClearObjects` 在本次核对中具有下述相同语义，但源码副本不会自动同步。Demo 资源页也没有执行独立模块的完整 `Init → StartLoading` 路径。

## 加载来源：先区分两层缓存

`ResourceSystem` 的 `resourceBuffer` 缓存的是资产对象；`GBundleBuilder` 选择的是 Bundle 的加载载体。对象缓存命中、Unity Bundle 缓存命中和本地文件存在是不同的条件。

独立模块的 [GBundleBuilder.cs](https://github.com/gonglei007/GGFramework-GGResource/blob/14c7a685b2b75686e5585f852d1bab93f5f46195/GGResource/Assets/Scripts/GGResource/Resource/GBundleBuilder.cs)按以下条件选择：

| 条件与顺序 | 实际行为 | 不能据此推断什么 |
|---|---|---|
| `useCache` 为 true，且 Unity 缓存命中 | 通过基于 BaseUri 的 Web 请求加载器使用缓存 | 不是默认开启，也不是 `resourceBuffer` 的引用计数 |
| 可写目录中存在目标 Bundle | 将加载基址换成 `BundleUtil.GetStorableDirectory()` | 文件存在不代表版本、哈希和内容已经验收 |
| 未命中可写目录，且只读目录命中 | 使用 `BundleUtil.GetReadOnlyDirectory()`；此分支受 WebGL 编译条件限制 | 不能把桌面文件访问直接外推到 WebGL / Android |
| 均未命中 | 保留构造时的 BaseUri；远程 URI 用网络加载器，本地 URI 用文件加载器 | 不会凭空得到 CDN 地址，也不代表失败后会自动换源重试 |

还需对照 [ResourceSystem.cs](https://github.com/gonglei007/GGFramework-GGResource/blob/14c7a685b2b75686e5585f852d1bab93f5f46195/GGResource/Assets/Scripts/GGResource/Systems/ResourceSystem.cs)的默认初始化：

- Editor 开启 Simulation 时使用模拟资源后端；运行时先从可写目录找 manifest，缺失才从只读目录找，不能将“存在但损坏”当作已实现自动回退。
- 默认创建 `GBundleBuilder` 时传入**只读目录 BaseUri、`useCache = false`、无解密器**。因此默认配置并不是“Unity 缓存 → 本地 → CDN”的完整在线方案。
- 加密 Bundle 还要求匹配的解密器；现有分支在不支持时抛出异常。网络地址、清单发布、下载校验、回滚和解密配置都应由接入工程明确提供。

## Demo 的三条资源路径

| 资源页操作 | 实际加载来源 | 缓存与退出方式 |
|---|---|---|
| 加载 / 获取引用 | `LocalResources.LoadAssetAsync<TextAsset>` 读取工程内 Resources 配置 | 首次创建运行时 `TextAsset` 副本，放入 Demo `ResourceSystem` 并 Retain；再次操作只增加同一缓存对象的引用 |
| Simulation 模拟加载 | Editor 的 `SimulationResources` 读取配置源资产，不需要预打包 | 使用临时 loader，在 `using` 内等待完成并读取文本；不进入 `ShowcaseConfig` 引用计数 |
| 加载真实 AssetBundle | `StreamingAssets/ShowcaseBundles` 中当前平台的 manifest 与 Bundle，通过 `FileAsyncBundleLoaderBuilder` 读取 | 临时 `BundleResources` 在完成读取后 Dispose；同样不进入 `ShowcaseConfig` 计数，也未走 `GBundleBuilder` 的远程选源 |

资源来源实现见 [FrameworkShowcase.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.cs)与 [FrameworkShowcase.Bundles.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/FrameworkShowcase.Bundles.cs)。三条路径最终都能显示配置文本，但不能相互替代验收。

## 引用计数：缓存查询不等于取得所有权

按独立模块的 [ResourceObject.cs](https://github.com/gonglei007/GGFramework-GGResource/blob/14c7a685b2b75686e5585f852d1bab93f5f46195/GGResource/Assets/Scripts/GGResource/Resource/ResourceObject.cs)与上述 `ResourceSystem.cs`：

| 调用或状态 | 计数与行为 | 调用方责任 |
|---|---|---|
| `new ResourceObject`，再 `SetObject` | 初始 `refCount = 0`；放入缓存本身不增加持有数 | 明确谁会持有它，不把“缓存存在”当作已被保护 |
| `GetObject` | 返回当前缓存项，不自动 Retain | 只查看状态可直接查询；开始持有时显式取得引用 |
| `Retain` | 命中时 `+1`；未命中静默返回 | 先确认资源存在，为每个持有者配对一次释放 |
| `DestroyObject`，计数大于 1 | 减 1，其他持有者仍可使用 | 清除自己保存的引用，不重复释放 |
| `DestroyObject`，计数为 1 或 0 | 归零或保持零，调用资产销毁并移除缓存 | 未 Retain 的旧调用也会被单次释放；不能依靠零计数缓存长期保护资产 |
| `ClearObjects(group)` / `ClearResources()` | 强制销毁并清空相应缓存，忽略计数；后者作用于当前 Group | 仅在所有持有者和在途请求都已退出的明确清理阶段使用 |

典型共享过程为：**缓存 0 → A 持有 1 → B 持有 2 → A 释放 1 → B 释放后移除**。当前计数是可变整数，没有持有者身份或释放句柄；A 误释放两次仍可能影响 B，计数并不会自动阻止这种错误。

缓存身份还要注意：

- 一级表键为 `group-tag`，二级键为 `assetName`，并不是完整 Bundle 路径；同桶内重名可能覆盖。`SetObject` 的替换分支没有实现旧资产释放，不应把它当作安全换版本接口。
- 两套 `ResourceSystem.Group` setter 当前都会将值写为 `"all"`。Demo 虽然赋值 `"showcase"`，实际仍使用统一组；不能据属性名认为已经实现大厅 / 战斗独立释放。
- `DestroyObject` / `ClearObjects` 没有同步清理 `assetsInBundle` 已加载记录。独立加载流程的“释放后再次加载”需要专门回归；Demo 的 LocalResources 手动入缓存流程不能证明它正确。

## 异步加载与释放责任

| 阶段或对象 | 当前实现与应有责任 |
|---|---|
| Demo 请求发起 | `ResourceBusy` 阻止重复在途加载，协程等待 `IsDone`，再检查异常和空结果；这不是多调用方请求合并或后台线程保证 |
| Demo 成功交付 | 将源配置文本复制到 `new TextAsset(...)` 后 SetObject + Retain。源资产与运行时副本不是同一个销毁对象；不要把项目导入资产直接交给此示例的 DestroyObject |
| Demo 正常释放 | 每次“释放一个引用”只释放自己取得的一份。两个持有者释放完后，缓存项移除；播放模式下 Unity 的 Destroy 是延后执行，不能据按钮状态推断内存当帧已下降 |
| Demo 场景退出 | `OnDestroy` 停止大厅协程、Dispose 本地 loader，并循环释放大厅专属缓存至移除；这依赖该配置专属的示例前提，不能照搬为共享业务资产的强制清理 |
| 独立模块的异步批量加载 | `StartLoading` 按非负优先级组织资源，成功资产通过回调入缓存。运行时分支失败也会触发 `onFinish` 推进流程；“一批结束”或完成数不等于全部成功 |
| Editor Simulation 失败 | `LoadBundleAssetsAsync` 的该分支 catch 记录错误，但没有运行时分支等价的 finally 推进逻辑；不能仅凭 Player 路径就声称 Editor 故障不会卡队列 |
| GameObject 实例与模板资产 | 业务创建的实例由业务或对象池回收；GGResource 的 `refCount` 不会统计场景中的所有实例引用，实例销毁也不会自动替调用者释放缓存持有 |
| Bundle 与底层依赖 | 由选用的 Loxodon 加载器 / Bundle 管理器另行管理。上层 ResourceObject 计数归零不代表 Bundle、依赖、Unity 缓存或 GPU 内存全部卸载 |

`LoadBundleAssetsAsync` 虽有 `unload` 参数，当前方法体没有消费它，不能按参数名承诺自动卸载。停止协程只停止这段本地等待，不能据此认定底层加载已取消。异步也不等于“离开页面就自动取消”：在独立模块中没有看到面向每个页面的代次 / 取消契约，接入方需要定义迟到结果的接收、丢弃和释放责任。

## 复现步骤与预期

按导读的[统一复现入口](GGFramework.md#运行一次完整体验)固定 Demo 并完成准备，再进入 **Play Showcase → 资源** 页，分别观察以下三种路径：

| 操作顺序 | 预期与观察对象 |
|---|---|
| 点击一次“加载 / 获取引用” | 等待完成，`ShowcaseConfig` 存在，计数为 1；缓存的是运行时副本 |
| 再点击一次 | 同一个 `ResourceObject`，计数为 2；身份对照可查看冒烟断言，不只看数字 |
| 点击一次“释放一个引用” | 计数为 1，配置仍可使用 |
| 再释放一次 | 缓存不存在，界面显示引用为 0；这不是进程内存已全部回收的测量 |
| 点击“加载缺失资源”，等待后再加载正常资源 | 失败可见、Busy 结束；随后正常资源仍可加载，结束后配对释放 |
| Editor 中点击“Simulation 模拟加载” | 显示配置文本；Player 不包含这个按钮 |
| 先执行“Build Sample Bundles”，再点击“加载真实 AssetBundle” | 当前平台清单与真实 Bundle 被读取，显示配置文本；不增加 ShowcaseConfig 引用 |

示例 Bundle 由 [ShowcaseTools.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/Editor/ShowcaseTools.cs)生成到 `Assets/StreamingAssets/ShowcaseBundles/`。菜单、批处理和报告路径统一见导读及其固定版本指南。

## 方案取舍与不适用场景

| 选择 | 适用条件 | 代价或边界 |
|---|---|---|
| Demo LocalResources + 专属运行时副本 | 先研究缓存身份、持有与配对释放 | 复制文本会新增分配；不能当作所有资产的通用复制或卸载策略 |
| Editor Simulation | 快速迭代资产和映射，不先构建 Bundle | 不验证平台 Bundle、发布清单、解密或网络下载 |
| 本地真实 Bundle | 验证当前平台的打包、清单和文件读取 | 仍需另测版本替换、资源依赖和卸载；不是远程热更验收 |
| 配置独立 GGResource 的加载来源 | 需要控制本地 / 网络来源、优先级和回调，能维护依赖 | 必须补充适合项目的资源身份、错误结果与生命周期契约 |
| 保留现有资源系统 | 团队已有成熟句柄、依赖管理或发布体系 | 可参考本篇责任划分，评估迁移成本，不必整体替换 |

不适用于直接宣称已实现按场景隔离、无泄漏卸载、自动 CDN 回退、取消后不再交付，或全平台稳定热更新。多页面共享资产、同名资源版本替换与加载中退出都要先建立明确所有权，不能靠清空统一组解决。

## 验证方法与证据边界

### 已有测试能说明什么

- 独立模块的 [ResourceSystemTests.cs](https://github.com/gonglei007/GGFramework-GGResource/blob/14c7a685b2b75686e5585f852d1bab93f5f46195/GGResource/Assets/Tests/EditMode/ResourceSystemTests.cs)覆盖内存态缓存 / 类型过滤、Retain 配对释放和强制清理。文件明确不覆盖 Init / Loxodon 运行时异步路径；需在该 Unity 工程的 Test Runner 中运行，不能拿本文的文档 CI 代替。
- Demo 的 [ShowcaseSmoke.cs](https://github.com/gonglei007/GGFramework-Demo/blob/e2a7586a1325fc8dd762b55d1105de81b9825154/unity_project/Assets/FrameworkShowcase/ShowcaseSmoke.cs)检查缓存身份及 `1 → 2 → 1 → 移除`、缺失资源失败状态、Editor Simulation 和真实本地 Bundle。缺失资源后恢复、最终运行时副本销毁、导入源保留及退出后专属缓存释放，由本轮新增生命周期回归另行断言；原有冒烟没有这些完整退出断言；也没有断言峰值内存、远程选源、页面退出竞态或所有 Bundle 已卸载。

本轮结果与未覆盖项见[运行记录](GGFrameworkUnity验证记录.md)；历史证据与 CI 的区别见导读的[证据分层](GGFramework.md#验证方法与证据边界)。完整大厅冒烟与独立 GGResource 的测试分别运行，不能互相替代。

本轮独立 GGResource EditMode 为 15/15；Demo 生命周期还记录了本地示例 Bundle 数量恢复为加载前值，并修复内置 Loxodon 的跨播放静态退出标记。它不证明全部 Bundle 依赖或 CPU / GPU 内存已释放，补丁没有自动传播到独立模块的第三方副本。

后续[自动化 CI](GGFramework自动化回归与CI.md)为独立 GGResource 增加 2 项 PlayMode：最后引用释放后原生 TextAsset 销毁，以及显式独占组清理后的缓存与原生对象释放。它们不初始化 Loxodon，也不证明共享同名资产或底层 Bundle 依赖已经安全释放。

### 接入前仍需验证

| 需要回答的问题 | 故障注入与验收要点 |
|---|---|
| 是否选到了预期来源 | 分别设置各目录命中 / 缺失、损坏 manifest、远程失败，记录最终 URI、版本和加载器 |
| 持有与释放是否正确 | 两个使用者共享、一个退出、另一个继续；检测重复释放、同桶重名和替换旧缓存 |
| 释放后能否重新加载 | 核对对象缓存、assetsInBundle 记录与底层状态一致，不能因已加载标记跳过实际重载 |
| 异步结束是否可靠 | 资源缺失、解码失败、回调异常；分别测 Simulation 和 Player，确认队列和 Busy 有明确终态 |
| 页面退出时谁收尾 | 加载中退出 / 重开页面，迟到结果不得更新旧页面，也不能泄漏或清掉其他使用者的引用 |
| 对象与 Bundle 是否真正释放 | 分别记录实例、模板、Bundle / 依赖、CPU / GPU 内存；等待合理回收时点后测量，不能只看计数为零 |
| 目标平台与发布是否成立 | 目标设备、后端、版本替换、下载校验、解密和回滚，保存实际报告 |

建议记录 `GGResource / Demo SHA、Core 版本、Unity、平台与后端、来源配置、资产身份、持有者、计数轨迹、请求终态和内存证据`。每个结论都对应实际运行范围。

## 图谱知识点映射

- [客户端底层通用系统](../../mds/3.研发能力/3.1.1.客户端底层通用系统.md)：资源缓存、生命周期与业务系统的释放责任。
- [产品热更新](../../mds/6.运营能力/6.2.3.产品热更新.md)：资源来源、版本、校验与回滚。
- [客户端优化](../../mds/3.研发能力/3.1.3.客户端优化.md)：加载峰值、实例与资产占用的实测。

继续阅读：[GGFramework 实践导读](GGFramework.md) · [客户端网络实践](GGFramework客户端网络实践.md) · [返回首页](../../README.md#可立即使用的资源)。
