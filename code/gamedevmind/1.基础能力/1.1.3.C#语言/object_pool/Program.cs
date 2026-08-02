using GameDevMind.Examples;

Console.WriteLine("=== C# 对象池演示 ===\n");

var pool = new ObjectPool<Bullet>(
    initialSize: 4,
    onGet: b => b.Active = true,
    onRelease: b => b.Reset()
);

// 模拟一帧内发射 6 颗子弹（池只有 4 个，会自动扩容）
var active = new List<Bullet>();
for (int i = 0; i < 6; i++)
{
    var bullet = pool.Get();
    bullet.X = i * 10f;
    bullet.Y = 100f;
    active.Add(bullet);
    Console.WriteLine($"  发射 bullet#{i} at ({bullet.X}, {bullet.Y})");
}

Console.WriteLine($"\n池中总数: {pool.CountAll}, 活跃: {active.Count}, 空闲: {pool.CountInactive}");

// 回收
foreach (var b in active)
    pool.Release(b);

Console.WriteLine($"回收后 — 总数: {pool.CountAll}, 空闲: {pool.CountInactive}");
Console.WriteLine("\n要点：Get/Release 替代 new/GC，帧率更稳定。");
