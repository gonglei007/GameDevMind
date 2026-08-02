## 社交系统开发 — 配套代码

对应文章：三-06 游戏社交系统

> 正文已瘦身：文章保留 4 个 Manager 骨架（约 50 行 C#），完整 Manager/Filter/关系图见 `social_system.py`。

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 好友 + 聊天 + 在线状态 | `social_system.py` | 好友申请/屏蔽、世界/公会/私聊频道、未读计数 |

### 文章章节覆盖

- **好友系统**：`FriendManager` 请求/接受/删除；`FriendRelation` 双向关系
- **聊天系统**：`ChatManager` 多频道缓存；`ChatFilter` 敏感词过滤
- **公会系统**：创建/申请/审批/捐献；`GuildRole` 职位权限
- **组队系统**：邀请/准备/开副本；队长权限校验
- **社交关系**：黑名单、好友的好友推荐

### 设计要点

- **好友关系**: `FriendRelation` 双向关系，支持 PENDING/FRIEND/BLOCKED 状态
- **聊天频道**: `ChatManager` 管理 World/Guild/Team/Whisper/System 多频道消息
- **在线状态**: ONLINE/BUSY/AWAY/INVISIBLE/OFFLINE 五种状态
- **未读计数**: 每个用户每个频道的未读消息数
- **屏蔽系统**: 屏蔽后无法发送好友申请

### 运行

```bash
python3 social_system.py
```
