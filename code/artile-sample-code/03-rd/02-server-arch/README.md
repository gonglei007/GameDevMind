## 服务端架构设计 — 配套代码

对应文章：三-02-游戏服务器架构演进：从单服到微服务

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 单服架构 / GameServer | `game_server.py` | TCP 连接、Session、消息分发 |
| 分布式 / Gateway | 正文接口骨架 | 负载均衡与转发逻辑 |
| 微服务 / 服务注册 | 正文接口骨架 | Register/Discover 模式 |
| 消息队列 / RabbitMQ | 正文生产者示例 | 完整消费者见 GameDevMind |
| 数据库 / 缓存 | 正文 Cache-Aside | 读写分离与 Redis 策略 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| Socket 房间服务器 | `game_server.py` | 创建/加入/离开房间、广播消息、心跳 |

### 设计要点

- **selectors 多路复用**: 单线程处理多客户端连接
- **房间管理**: CREATE/JOIN/LEAVE/LIST/WHO 完整生命周期
- **广播**: 房间内 SAY 消息向其他成员转发
- **心跳**: 独立线程每 10s 检查，30s 超时断开

### 运行

```bash
# 启动服务器（等待外部连接）
python3 game_server.py

# 带模拟客户端演示
python3 game_server.py --demo

# 用 telnet/nc 连接
nc localhost 9000
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
