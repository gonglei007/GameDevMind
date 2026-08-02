## 网络通信 — 配套代码

对应文章：二-05-TCP vs UDP，游戏网络通信该怎么选？

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 协议设计 / 序列化 | `net_demo.py` | JSON/binary 消息打包 |
| 心跳与重连 | `net_demo.py` | 心跳包、超时检测 |
| 状态同步 | `net_demo.py` | 简化状态广播与插值 |
| TCP/UDP Socket | 正文为 C# 骨架 | 完整多连接服务器见 GameDevMind |

### 运行

```bash
python3 net_demo.py
```

纯标准库，无需安装依赖。

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
