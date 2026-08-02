#!/usr/bin/env python3
"""
网络通信演示 — 消息序列化(JSON/binary对比) + 心跳包 + 状态同步

纯标准库实现，模拟游戏网络层核心机制：
1. 消息序列化 — JSON 文本格式 vs 二进制紧凑格式对比
2. 心跳机制 — 每2秒发送心跳包，超时3次判定断线
3. 状态同步 — 客户端预测 + 服务端权威校正

运行：python net_demo.py
"""

import json
import struct
import time
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple


# ══════════════════════════════════════════════
# 1. 消息序列化对比 (JSON vs Binary)
# ══════════════════════════════════════════════

class MessageSerializer:
    """对比两种序列化方式的开销"""

    @staticmethod
    def to_json(msg_type: int, data: dict) -> bytes:
        """JSON 格式：可读性好，但体积大"""
        payload = json.dumps({"t": msg_type, "d": data}, separators=(",", ":"))
        return payload.encode("utf-8")

    @staticmethod
    def from_json(raw: bytes) -> Tuple[int, dict]:
        obj = json.loads(raw.decode("utf-8"))
        return obj["t"], obj["d"]

    @staticmethod
    def to_binary(msg_type: int, data: dict) -> bytes:
        """二进制格式：紧凑但不可读。格式：[msg_type:1B][key_count:2B][for each: key_len:1B,key,val]"""
        buf = bytearray()
        buf.append(msg_type & 0xFF)                    # 消息类型 1B
        buf.extend(struct.pack(">H", len(data)))       # 键数量 2B (big-endian)
        for k, v in data.items():
            kb = k.encode("utf-8")
            buf.append(len(kb) & 0xFF)                 # key长度 1B
            buf.extend(kb)                             # key字节
            if isinstance(v, float):
                buf.extend(struct.pack(">f", v))       # float 4B
            elif isinstance(v, int):
                buf.extend(struct.pack(">i", v))       # int 4B
            elif isinstance(v, str):
                vb = v.encode("utf-8")
                buf.append(len(vb) & 0xFF)
                buf.extend(vb)
        return bytes(buf)

    @staticmethod
    def from_binary(raw: bytes) -> Tuple[int, dict]:
        offset = 0
        msg_type = raw[offset]; offset += 1
        key_count = struct.unpack(">H", raw[offset:offset+2])[0]; offset += 2
        data = {}
        for _ in range(key_count):
            key_len = raw[offset]; offset += 1
            key = raw[offset:offset+key_len].decode("utf-8"); offset += key_len
            # 简单推断：尝试解析为 float
            try:
                val = struct.unpack(">f", raw[offset:offset+4])[0]; offset += 4
            except struct.error:
                val_len = raw[offset]; offset += 1
                val = raw[offset:offset+val_len].decode("utf-8"); offset += val_len
            data[key] = val
        return msg_type, data


def demo_serialization():
    """演示序列化对比"""
    test_data = {"x": 1.5, "y": 2.3, "hp": 100, "name": "player1"}

    json_bytes = MessageSerializer.to_json(1, test_data)
    bin_bytes = MessageSerializer.to_binary(1, test_data)

    print("═══ 序列化对比 ═══")
    print(f"  JSON:   {len(json_bytes):>4} bytes → {json_bytes!r}")
    print(f"  Binary: {len(bin_bytes):>4} bytes → {bin_bytes.hex()}")
    print(f"  节省:   {(1 - len(bin_bytes)/len(json_bytes)) * 100:.0f}%")

    # 反序列化验证
    jt, jd = MessageSerializer.from_json(json_bytes)
    bt, bd = MessageSerializer.from_binary(bin_bytes)
    print(f"  JSON 还原:   type={jt}, data={jd}")
    print(f"  Binary 还原: type={bt}, data={bd}")
    print()


# ══════════════════════════════════════════════
# 2. 心跳机制
# ══════════════════════════════════════════════

@dataclass
class HeartbeatManager:
    """心跳管理：2秒间隔，3次超时断线"""
    interval: float = 2.0           # 心跳间隔(秒)
    timeout_limit: int = 3          # 连续超时上限
    last_send: float = 0.0          # 上次发送时间
    last_recv: float = 0.0          # 上次收到心跳
    missed_count: int = 0           # 连续未收到次数
    connected: bool = True

    def should_send_heartbeat(self, now: float) -> bool:
        """是否到时间发送心跳"""
        return self.connected and (now - self.last_send) >= self.interval

    def send_heartbeat(self, now: float):
        """发送心跳"""
        self.last_send = now

    def receive_heartbeat(self, now: float):
        """收到心跳回应"""
        self.last_recv = now
        self.missed_count = 0

    def check_timeout(self, now: float) -> bool:
        """检测是否超时断线"""
        if not self.connected:
            return False
        if (now - self.last_recv) > self.interval * self.timeout_limit:
            self.missed_count += 1
            if self.missed_count >= self.timeout_limit:
                self.connected = False
                return True
        return False

    def status(self) -> str:
        if not self.connected:
            return "❌ 断线"
        return "🟢 在线"


def demo_heartbeat():
    """演示心跳机制"""
    print("═══ 心跳机制演示 (2秒间隔, 3次超时断线) ═══")

    hb = HeartbeatManager()
    sim_start = time.time()

    # 模拟 10 秒运行，第 5-8 秒模拟网络中断
    for sec in range(11):
        now = sim_start + sec

        if hb.should_send_heartbeat(now):
            hb.send_heartbeat(now)
            action = "📤 发送心跳"
        else:
            action = "   —"

        # 模拟：5-8 秒不回应（网络中断）
        if not (5 <= sec <= 8):
            hb.receive_heartbeat(now)
            ack = "📥 收到回应"
        else:
            ack = "⚠️  无回应(模拟丢包)"

        disconnected = hb.check_timeout(now)

        print(f"  t={sec:2d}s | {action:14s} | {ack:20s} | {hb.status()}")

        if disconnected:
            print(f"  ═══ 第 {sec} 秒：连接断开！连续 {hb.timeout_limit} 次未收到心跳 ═══")
            break

    print()


# ══════════════════════════════════════════════
# 3. 状态同步
# ══════════════════════════════════════════════

@dataclass
class PlayerState:
    """玩家状态"""
    player_id: str
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    seq: int = 0       # 序列号，用于去重和确认


class StateSyncDemo:
    """演示客户端预测 + 服务端权威校正"""

    def __init__(self):
        self.server_state = PlayerState("p1", 0.0, 0.0)
        self.client_state = PlayerState("p1", 0.0, 0.0)
        self.pending_inputs: deque = deque()  # 未确认的输入队列
        self.sync_log: list = []

    def client_tick(self, dt: float, input_dx: float, input_dy: float) -> PlayerState:
        """客户端帧：本地预测移动"""
        self.client_state.vx = input_dx
        self.client_state.vy = input_dy
        self.client_state.x += input_dx * dt
        self.client_state.y += input_dy * dt
        self.client_state.seq += 1

        # 记录未确认输入
        self.pending_inputs.append((self.client_state.seq, input_dx, input_dy))
        # 限制队列长度
        if len(self.pending_inputs) > 10:
            self.pending_inputs.popleft()

        return self.client_state

    def server_tick(self, dt: float):
        """服务端帧：权威物理计算"""
        # 服务端用自己保存的速度（来自最近收到的输入）
        self.server_state.x += self.server_state.vx * dt
        self.server_state.y += self.server_state.vy * dt

    def server_receive_input(self, seq: int, dx: float, dy: float):
        """服务端收到玩家输入"""
        self.server_state.vx = dx
        self.server_state.vy = dy
        self.server_state.seq = seq

    def reconcile(self):
        """客户端收到服务端状态后做校正：重新应用未确认的输入"""
        corrected = PlayerState(
            player_id=self.client_state.player_id,
            x=self.server_state.x,
            y=self.server_state.y,
            vx=self.server_state.vx,
            vy=self.server_state.vy,
            seq=self.server_state.seq,
        )
        # 重新应用所有未确认的输入
        for seq, dx, dy in self.pending_inputs:
            if seq > self.server_state.seq:
                corrected.x += dx * 0.1  # 假设 dt=0.1
                corrected.y += dy * 0.1

        old = (self.client_state.x, self.client_state.y)
        self.client_state = corrected
        new = (self.client_state.x, self.client_state.y)
        drift = ((new[0] - old[0]) ** 2 + (new[1] - old[1]) ** 2) ** 0.5
        return drift


def demo_state_sync():
    """演示状态同步"""
    print("═══ 状态同步演示 (客户端预测 + 服务端校正) ═══")

    sync = StateSyncDemo()
    inputs = [(1.0, 0.0), (1.0, 0.5), (0.0, -1.0), (-0.5, 0.0)]
    dt = 0.1

    for i, (dx, dy) in enumerate(inputs):
        # 客户端预测
        client = sync.client_tick(dt, dx, dy)
        print(f"\n  Tick {i + 1}: 输入=({dx},{dy})")
        print(f"    客户端预测: pos=({client.x:.2f}, {client.y:.2f}) seq={client.seq}")

        # 模拟网络延迟：服务端稍后才处理
        jitter = random.uniform(0, 0.05)
        # 服务端权威计算
        sync.server_receive_input(client.seq - 1 if client.seq > 1 else 0, dx, dy)
        sync.server_tick(dt + jitter)
        print(f"    服务端权威: pos=({sync.server_state.x:.2f}, {sync.server_state.y:.2f}) seq={sync.server_state.seq}")

        # 校正
        drift = sync.reconcile()
        print(f"    校正后:     pos=({sync.client_state.x:.2f}, {sync.client_state.y:.2f}) 漂移={drift:.3f}")

    print(f"\n  最终 客户端: ({sync.client_state.x:.2f}, {sync.client_state.y:.2f})")
    print(f"  最终 服务端: ({sync.server_state.x:.2f}, {sync.server_state.y:.2f})")
    print()


# ══════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  游戏网络通信演示")
    print("  消息序列化 | 心跳机制 | 状态同步")
    print("=" * 60)
    print()

    # 1. 序列化对比
    demo_serialization()

    # 2. 心跳机制
    demo_heartbeat()

    # 3. 状态同步
    demo_state_sync()

    print("=" * 60)
    print("  演示完成！")
    print("  核心：JSON vs Binary 序列化 → 心跳保活 → 客户端预测+服务端校正")
    print("=" * 60)


if __name__ == "__main__":
    main()
