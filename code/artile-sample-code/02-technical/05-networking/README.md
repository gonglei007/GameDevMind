# 网络通信 — 配套代码

配套正文：[网络与通信](../../../../mds/2.技术能力/2.2.1.网络与通信.md)。纯 Python 标准库，Python 3.11+；这是正确性教学，不是生产网络栈。

## 契约与边界

| 模块 | 行为 | 未覆盖范围 |
|------|------|------|
| MessageSerializer | JSON 与 GN/version=1 二进制；显式 int64/float64/UTF-8 标签，拒绝非法类型、重复键与截断 | schema 演进、跨语言精度、压缩、加密 |
| FrameDecoder | u32 网络序长度；正文 1–65536 字节，单次 feed 至多 65540；支持任意拆分/合并，拒绝半帧 EOF | Socket 头/正文超时、全局连接/调度预算 |
| SendBuffer | 默认最多 131080 字节排队；保留部分发送，暂不可写不丢字节，超预算显式报错 | 事件循环、业务分类的拒绝/降级策略 |
| HeartbeatManager | 单调时间，2 秒探测/6 秒截止；单个未确认探针，代次/序号匹配，过期不复活 | 真实心跳收发、重连、认证、防伪造 |
| StateSyncDemo | 本地二维线性模型；按连续输入前缀确认，以原 dt 重放；序号不回退，最多 32 个待确认输入 | UDP 缺口恢复实现、物理、插值、AOI、反作弊 |

二进制头 `GN` + 版本 u8 + 类型 u8 + 字段数 u16；键为 u8 字节长 + UTF-8，值标签 1=int64、2=float64、3=u16 字节长 + UTF-8。至多 64 字段，键 1–255 字节，字符串至多 4096 字节，禁止非有限浮点数。教学格式不替代成熟 schema。

输入必须连续、dt 在 (0, 0.25]、方向分量在 [-1, 1]；确认输入号与快照号独立。缺口/积压溢出抛出 ResyncRequired，调用方必须设计恢复，不能继续静默丢输入。停止也是有序输入。

## 运行与验证

在仓库根目录执行：

```bash
python code/artile-sample-code/02-technical/05-networking/net_demo.py
python -m unittest discover -s code/artile-sample-code/02-technical/05-networking -p 'test_*.py' -v
```

测试覆盖精确类型往返、非法消息、每个拆分点、部分写入、背压、超时频率独立、旧代次回包、变 dt 重放、未来/旧确认和积压预算。Windows/Linux CI 均执行；CLI 输出大小是当前载荷的演示，不是序列化性能基准。

真实 TCP/UDP 回环见 [socket_demo](../../01-foundation/06-os-network/)，C++ 同步模型见 [network_sync](../../../gamedevmind/2.技术能力/2.2.1.网络与通信/network_sync/)。仓库其他架构骨架不构成本目录测试覆盖，不能由本回归推断其生产就绪。
