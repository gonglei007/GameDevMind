# 操作系统与计算机网络基础 — Socket 教学

配套 [网络与通信](../../../../mds/2.技术能力/2.2.1.网络与通信.md)，复用 [net_demo](../../02-technical/05-networking/) 的长度分帧器。Python 3.11+，纯标准库；需要同时保留仓库内这两个目录。

## 适用条件与边界

- TCP：真实 127.0.0.1 回环，用临时端口、3 秒 Socket 超时和受控工作线程；故意拆写/小块读，正确解析并逐消息回显。TCP ACK 不等于业务提交，echo 只说明此处理器执行。
- UDP：每包 16 字节（u32 序号 + 三个 float32，网络序），人工省略 3/6、重复 5、在 5 后送 4，接收方采纳 [1, 2, 5, 7, 8]。这验证可替换快照的单调更新，不表示射击/交易可丢。
- 畸形长度、非有限坐标和非法序号拒绝；旧/重复包不回退状态。未实现序号回绕，重新建立会话应隔离旧报文。

没有随机“30% 丢包率”或真实网络性能结论；序号缺口也可能因乱序/延迟，不能直接记永久丢包。没有 TLS/认证、拥塞控制、NAT、弱网、容量或长连接服务验证。TCP helper 限教学小批消息，先发后读不适合无限双向流或大批压测。

## 运行与验证

在仓库根目录执行：

```bash
python code/artile-sample-code/01-foundation/06-os-network/socket_demo.py
python -m unittest discover -s code/artile-sample-code/01-foundation/06-os-network -p 'test_*.py' -v
```

Windows/Linux CI 执行真实 TCP/UDP 回环和错误报文测试；断言消息完全一致、重复/乱序不回退，线程异常与超时使运行失败。纯协议的部分写入/背压/分帧边界另由 net_demo 回归验证。
