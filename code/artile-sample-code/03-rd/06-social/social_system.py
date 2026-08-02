#!/usr/bin/env python3
"""
社交系统演示：好友系统 + 聊天频道 + 在线状态管理
纯标准库，直接运行。

功能：
  - 好友系统：添加/删除/黑名单/好友申请
  - 聊天频道：世界/队伍/私聊
  - 在线状态：在线/忙碌/离线/隐身
  - 消息存储与未读计数
"""

from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time
import uuid


# ─── 在线状态 ─────────────────────────────────────────────────────
class OnlineStatus(Enum):
    ONLINE = "🟢 在线"
    BUSY = "🔴 忙碌"
    AWAY = "🟡 离开"
    INVISIBLE = "⚫ 隐身"
    OFFLINE = "⭕ 离线"


# ─── 好友关系 ─────────────────────────────────────────────────────
class FriendStatus(Enum):
    NONE = "无关系"
    PENDING = "待确认"       # A→B 发出申请
    FRIEND = "好友"
    BLOCKED = "已屏蔽"


@dataclass
class FriendRelation:
    """双向好友关系"""
    user_a: str
    user_b: str
    status: FriendStatus = FriendStatus.NONE
    initiator: str = ""        # 谁发出的申请
    since: float = 0.0

    def other(self, name: str) -> str:
        return self.user_b if name == self.user_a else self.user_a


# ─── 聊天频道 ────────────────────────────────────────────────────
class ChannelType(Enum):
    WORLD = "世界"
    TEAM = "队伍"
    GUILD = "公会"
    WHISPER = "私聊"
    SYSTEM = "系统"


@dataclass
class ChatMessage:
    id: str
    channel: ChannelType
    channel_id: str       # 频道标识（队伍名/用户名等）
    sender: str
    content: str
    timestamp: float = field(default_factory=time.time)

    def format(self) -> str:
        t = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[{t}] [{self.channel.value}] {self.sender}: {self.content}"


# ─── 聊天管理器 ──────────────────────────────────────────────────
class ChatManager:
    """管理所有频道的消息"""

    MAX_HISTORY = 100  # 每频道最多保留

    def __init__(self):
        self.channels: dict[tuple[ChannelType, str], list[ChatMessage]] = defaultdict(list)
        self.unread: dict[str, dict[tuple[ChannelType, str], int]] = defaultdict(
            lambda: defaultdict(int))

    def send(self, channel: ChannelType, channel_id: str,
             sender: str, content: str) -> ChatMessage:
        msg = ChatMessage(
            id=str(uuid.uuid4())[:8],
            channel=channel,
            channel_id=channel_id,
            sender=sender,
            content=content,
        )
        key = (channel, channel_id)
        self.channels[key].append(msg)
        if len(self.channels[key]) > self.MAX_HISTORY:
            self.channels[key] = self.channels[key][-self.MAX_HISTORY:]

        # 增加其他参与者的未读计数
        # （简化：频道以 channel_id 标识，私聊 channel_id 是对方名）
        return msg

    def get_history(self, channel: ChannelType, channel_id: str,
                    limit: int = 20) -> list[ChatMessage]:
        key = (channel, channel_id)
        msgs = self.channels[key]
        return msgs[-limit:]

    def mark_read(self, user: str, channel: ChannelType, channel_id: str):
        self.unread[user][(channel, channel_id)] = 0

    def get_unread_count(self, user: str, channel: ChannelType,
                         channel_id: str) -> int:
        return self.unread[user].get((channel, channel_id), 0)


# ─── 社交管理器 ──────────────────────────────────────────────────
class SocialManager:
    """统一社交系统"""

    def __init__(self):
        self.users: dict[str, dict] = {}         # name → {status, level, guild}
        self.relations: dict[tuple[str, str], FriendRelation] = {}  # (name1,name2) sorted
        self.chat = ChatManager()

    # ── 用户管理 ──
    def register(self, name: str, level: int = 1):
        if name in self.users:
            return False
        self.users[name] = {
            "status": OnlineStatus.ONLINE,
            "level": level,
            "guild": "",
            "join_time": time.time(),
        }
        print(f"👤 {name} 注册成功 (Lv.{level})")
        return True

    def set_status(self, name: str, status: OnlineStatus):
        if name not in self.users:
            return
        old = self.users[name]["status"]
        self.users[name]["status"] = status
        print(f"📡 {name}: {old.value} → {status.value}")

    def get_status(self, name: str) -> OnlineStatus:
        if name not in self.users:
            return OnlineStatus.OFFLINE
        return self.users[name]["status"]

    # ── 好友系统 ──
    def _relation_key(self, a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    def add_friend_request(self, from_user: str, to_user: str) -> bool:
        """发送好友申请"""
        if from_user not in self.users or to_user not in self.users:
            print(f"❌ 用户不存在")
            return False
        if from_user == to_user:
            print(f"❌ 不能添加自己")
            return False

        key = self._relation_key(from_user, to_user)
        if key in self.relations:
            rel = self.relations[key]
            if rel.status == FriendStatus.FRIEND:
                print(f"❌ 已经是好友")
                return False
            if rel.status == FriendStatus.BLOCKED:
                print(f"❌ 已被屏蔽")
                return False
            if rel.status == FriendStatus.PENDING:
                print(f"❌ 已有待确认申请")
                return False

        self.relations[key] = FriendRelation(
            user_a=key[0], user_b=key[1],
            status=FriendStatus.PENDING,
            initiator=from_user,
            since=time.time(),
        )
        print(f"📨 {from_user} → {to_user} 好友申请已发送")
        return True

    def accept_friend(self, accepter: str, requester: str) -> bool:
        """接受好友申请"""
        key = self._relation_key(accepter, requester)
        if key not in self.relations:
            print(f"❌ 没有待处理的申请")
            return False
        rel = self.relations[key]
        if rel.status != FriendStatus.PENDING:
            print(f"❌ 申请状态异常: {rel.status}")
            return False
        if rel.initiator != requester:
            print(f"❌ 申请方向不匹配")
            return False

        rel.status = FriendStatus.FRIEND
        print(f"✅ {accepter} 和 {requester} 成为好友！")

        # 系统通知
        self.chat.send(ChannelType.SYSTEM, requester, "系统",
                       f"{accepter} 已接受你的好友申请")
        self.chat.send(ChannelType.SYSTEM, accepter, "系统",
                       f"你和 {requester} 成为了好友")
        return True

    def remove_friend(self, user: str, friend: str) -> bool:
        """删除好友"""
        key = self._relation_key(user, friend)
        if key not in self.relations:
            print(f"❌ 不是好友")
            return False
        rel = self.relations[key]
        if rel.status != FriendStatus.FRIEND:
            print(f"❌ 不是好友")
            return False
        del self.relations[key]
        print(f"💔 {user} 删除了好友 {friend}")
        return True

    def block_user(self, user: str, target: str) -> bool:
        """屏蔽用户"""
        key = self._relation_key(user, target)
        if key in self.relations:
            del self.relations[key]
        self.relations[key] = FriendRelation(
            user_a=key[0], user_b=key[1],
            status=FriendStatus.BLOCKED,
            initiator=user,
            since=time.time(),
        )
        print(f"🚫 {user} 屏蔽了 {target}")
        return True

    def get_friends(self, user: str) -> list[str]:
        """获取好友列表"""
        friends = []
        for key, rel in self.relations.items():
            if rel.status == FriendStatus.FRIEND and user in key:
                friends.append(rel.other(user))
        return sorted(friends)

    def get_pending_requests(self, user: str) -> list[str]:
        """获取待处理好友申请"""
        pending = []
        for key, rel in self.relations.items():
            if rel.status == FriendStatus.PENDING and user in key and rel.initiator != user:
                pending.append(rel.other(user))
        return pending

    def print_friend_list(self, user: str):
        """打印好友列表（含在线状态）"""
        friends = self.get_friends(user)
        if not friends:
            print(f"  📭 {user} 暂无好友")
            return
        print(f"\n  📋 {user} 的好友列表 ({len(friends)}):")
        for f in sorted(friends):
            status = self.get_status(f)
            print(f"    {status.value} {f}")

    # ── 聊天 ──
    def send_whisper(self, sender: str, receiver: str, content: str):
        """私聊"""
        if sender == receiver:
            print("❌ 不能给自己发私聊")
            return
        self.chat.send(ChannelType.WHISPER, receiver, sender, content)

    def send_world(self, sender: str, content: str):
        """世界频道"""
        self.chat.send(ChannelType.WORLD, "global", sender, content)

    def show_channel(self, channel: ChannelType, channel_id: str,
                     limit: int = 10):
        """显示频道消息"""
        msgs = self.chat.get_history(channel, channel_id, limit)
        if not msgs:
            print(f"  📭 [{channel.value}] 暂无消息")
            return
        print(f"\n  ── [{channel.value}] 最近 {len(msgs)} 条消息 ──")
        for m in msgs:
            print(f"  {m.format()}")


# ─── 演示 ────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  社交系统演示 — 好友 + 聊天频道 + 在线状态")
    print("=" * 60)

    sm = SocialManager()

    # 1. 注册用户
    print("\n📝 1. 用户注册")
    sm.register("Alice", level=50)
    sm.register("Bob", level=48)
    sm.register("Cathy", level=55)
    sm.register("Dave", level=32)

    # 2. 好友系统
    print("\n👥 2. 好友系统")
    sm.add_friend_request("Alice", "Bob")
    sm.add_friend_request("Alice", "Cathy")
    sm.add_friend_request("Bob", "Dave")

    print(f"\n  Alice 待处理申请: {sm.get_pending_requests('Alice')}")
    print(f"  Bob 待处理申请: {sm.get_pending_requests('Bob')}")
    print(f"  Dave 待处理申请: {sm.get_pending_requests('Dave')}")

    sm.accept_friend("Bob", "Alice")
    sm.accept_friend("Cathy", "Alice")

    sm.print_friend_list("Alice")
    sm.print_friend_list("Bob")

    # 3. 在线状态
    print("\n📡 3. 在线状态")
    sm.set_status("Bob", OnlineStatus.BUSY)
    sm.set_status("Cathy", OnlineStatus.AWAY)

    sm.print_friend_list("Alice")

    # 4. 聊天
    print("\n💬 4. 聊天频道")

    print("\n  [世界频道]")
    sm.send_world("Alice", "有人组队下副本吗？")
    sm.send_world("Bob", "我！需要一个治疗")
    sm.send_world("Cathy", "等我5分钟，马上好")
    sm.show_channel(ChannelType.WORLD, "global")

    print("\n  [私聊]")
    sm.send_whisper("Alice", "Bob", "副本入口集合？")
    sm.send_whisper("Bob", "Alice", "好的，马上到")
    sm.show_channel(ChannelType.WHISPER, "Bob")
    print()
    sm.show_channel(ChannelType.WHISPER, "Alice")

    # 5. 屏蔽
    print("\n🚫 5. 屏蔽功能")
    sm.block_user("Alice", "Dave")
    result = sm.add_friend_request("Dave", "Alice")
    print(f"  Dave 尝试添加 Alice 好友: {'成功' if result else '被拒绝'}")

    # 6. 删除好友
    print("\n💔 6. 删除好友")
    sm.remove_friend("Alice", "Bob")
    sm.print_friend_list("Alice")

    print(f"\n✅ 社交系统演示完成")


if __name__ == "__main__":
    main()
