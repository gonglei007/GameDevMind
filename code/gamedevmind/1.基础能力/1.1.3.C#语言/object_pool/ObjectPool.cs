using System;
using System.Collections.Generic;

namespace GameDevMind.Examples;

/// <summary>
/// 泛型对象池 — Unity 子弹/粒子/UI 列表项等高频创建销毁场景的常用优化手段。
/// 对应文档：mds/1.基础能力/1.1.3.C#语言.md
/// </summary>
public sealed class ObjectPool<T> where T : class, new()
{
    private readonly Stack<T> _free = new();
    private readonly Action<T>? _onGet;
    private readonly Action<T>? _onRelease;
    private int _totalCreated;

    public ObjectPool(int initialSize = 32, Action<T>? onGet = null, Action<T>? onRelease = null)
    {
        _onGet = onGet;
        _onRelease = onRelease;
        Grow(initialSize);
    }

    public int CountInactive => _free.Count;
    public int CountAll => _totalCreated;

    public T Get()
    {
        var item = _free.Count > 0 ? _free.Pop() : CreateOne();
        _onGet?.Invoke(item);
        return item;
    }

    public void Release(T item)
    {
        if (item is null) throw new ArgumentNullException(nameof(item));
        _onRelease?.Invoke(item);
        _free.Push(item);
    }

    public void Clear() => _free.Clear();

    private void Grow(int count)
    {
        for (int i = 0; i < count; i++)
            _free.Push(CreateOne());
    }

    private T CreateOne()
    {
        _totalCreated++;
        return new T();
    }
}

/// <summary>演示用：模拟子弹对象</summary>
public sealed class Bullet
{
    public float X { get; set; }
    public float Y { get; set; }
    public bool Active { get; set; }

    public void Reset()
    {
        X = Y = 0;
        Active = false;
    }
}
