# C# 对象池示例

Unity / 手游客户端中子弹、粒子、伤害数字等对象每帧大量创建销毁，对象池是控制 GC 抖动的常用手段。

对应文档：[C#语言](../../../../mds/1.基础能力/1.1.3.C#语言.md)

## 快速运行

```bash
cd object_pool
dotnet run
```

## 核心 API

| 方法 | 说明 |
|------|------|
| `Get()` | 从池中取对象（池空则新建） |
| `Release(item)` | 归还对象到池 |
| `onGet` / `onRelease` | 可选回调，对应 Unity 中 `SetActive(true/false)` |

## 与 C++ 版对比

仓库中 [object_pool（C++）](../../1.2.1.设计模式/object_pool/) 演示相同模式，C# 版可直接嵌入 Unity 项目（去掉 `Program.cs` 即可）。

## 延伸

- 图谱：[设计模式 · 对象池](../../1.2.1.设计模式/object_pool/)
- 案例：[SLG 内存泄漏](../../../../cases/memory-leak-slg.md)（错误使用引用导致的反面教材）
