# C++17 锁序回归

对应 [ABBA 案例](../../../../../cases/server-deadlock.md) 和 [服务端优化](../../../../../mds/3.研发能力/3.2.3.服务端优化.md)。修正旧稿中“先复制成员，再持 Player 嵌套获取 Guild”的反序路径。

## 验证范围

1. 两阶段屏障使双方持有第一把锁时尝试第二把，验证 ABBA 循环等待条件；使用 try_lock 并最终释放，测试不故意永久挂死。
2. 多线程统一 Guild → Player 层级，检查完成计数与双对象不变量。
3. scoped_lock 的调用方交换参数顺序，验证该夹具下的避免死锁路径。
4. 失效成员关系在同一锁边界检查，被拒操作不更改状态。

这不是生产 Guild/Player 生命周期实现。调用方不能预先持有这两把非递归锁；多个同层对象、其他外围锁、回调和 IO 还需设计。std::scoped_lock 不保证硬件原子地同时拿到多把锁。没有运行 TSan 不应声称已通过数据竞争检测；ASan/UBSan 也不能代替 TSan 或证明不存在死锁。

## 运行

Linux，支持 C++17 的编译器和 pthread：

```bash
c++ -std=c++17 -Wall -Wextra -Werror -pthread -g \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  lock_order_regression.cpp -o /tmp/server-lock-order
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 timeout 20s /tmp/server-lock-order
```

也可 `cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure`。CTest 设置 20 秒超时；CI 同样使用外部 timeout，进度回归必须失败，不忽略错误。

通过仅证明此夹具的结果，不证明整个服务无锁环，更不推导线上“半年零死锁”。真实稳定性验证需线程/锁记录、并发场景、不变量与明确的观测窗口。
