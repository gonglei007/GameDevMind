#!/usr/bin/env python3
"""
网络同步演示：客户端预测 + 服务器和解 + 实体插值
纯标准库，直接运行。

模拟：
  - 客户端预测：立即响应输入，不等服务器
  - 服务器权威：收到输入后做权威计算
  - 和解 (Reconciliation)：服务器发回校正位置
  - 实体插值：客户端在两次服务器状态间插值

模拟 100ms 网络延迟，展示同步过程。
"""

import time
import random
import math
from collections import deque
from dataclasses import dataclass, field


# ─── 网络模拟 ─────────────────────────────────────────────────────
NETWORK_DELAY = 0.100  # 100ms 模拟延迟


class NetworkSimulator:
    """模拟网络延迟的消息队列"""

    def __init__(self, delay=NETWORK_DELAY):
        self.delay = delay
        self.queue: deque = deque()

    def send(self, message):
        """发送消息（带延迟投递）"""
        deliver_at = time.time() + self.delay
        self.queue.append((deliver_at, message))

    def receive(self) -> list:
        """取回所有到期的消息"""
        now = time.time()
        ready = []
        remaining = deque()
        while self.queue:
            deliver_at, msg = self.queue.popleft()
            if deliver_at <= now:
                ready.append(msg)
            else:
                remaining.append((deliver_at, msg))
        self.queue = remaining
        return ready


# ─── 游戏状态 ─────────────────────────────────────────────────────
@dataclass
class PlayerState:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    timestamp: float = 0.0


# ─── 客户端 ──────────────────────────────────────────────────────
class Client:
    TICK_RATE = 0.016  # ~60fps
    MOVE_SPEED = 200.0  # 像素/秒

    def __init__(self, player_id: int, to_server: NetworkSimulator, from_server: NetworkSimulator):
        self.player_id = player_id
        self.to_server = to_server
        self.from_server = from_server

        # 客户端预测状态
        self.predicted: PlayerState = PlayerState()
        self.server_authority: PlayerState | None = None  # 最近收到的服务器状态

        # 未确认的输入（用于和解）
        self.pending_inputs: deque = deque()
        self.input_seq = 0

        # 其他玩家插值
        self.other_players: dict[int, tuple[PlayerState, PlayerState]] = {}  # id -> (prev, next)

        self.sim_time = 0.0

    def apply_input(self, dx: float, dy: float):
        """处理玩家输入 — 客户端预测"""
        self.input_seq += 1
        dt = self.TICK_RATE

        # 客户端立即预测
        self.predicted.vx = dx * self.MOVE_SPEED
        self.predicted.vy = dy * self.MOVE_SPEED
        self.predicted.x += self.predicted.vx * dt
        self.predicted.y += self.predicted.vy * dt
        self.predicted.timestamp = self.sim_time

        # 发送输入到服务器
        input_msg = {
            "type": "input",
            "player": self.player_id,
            "seq": self.input_seq,
            "dx": dx,
            "dy": dy,
            "timestamp": self.sim_time,
        }
        self.to_server.send(input_msg)
        self.pending_inputs.append(input_msg)

        # 限制未确认队列
        if len(self.pending_inputs) > 60:
            self.pending_inputs.popleft()

    def update(self):
        """每帧更新"""
        self.sim_time += self.TICK_RATE

        # 接收服务器消息
        for msg in self.from_server.receive():
            self._handle_server_msg(msg)

    def _handle_server_msg(self, msg: dict):
        if msg["type"] == "state":
            # 服务器权威状态
            server_state = PlayerState(
                x=msg["x"],
                y=msg["y"],
                vx=msg.get("vx", 0),
                vy=msg.get("vy", 0),
                timestamp=msg["timestamp"],
            )
            last_processed = msg.get("last_processed_seq", 0)
            self.server_authority = server_state

            # 和解：移除服务器已确认的输入，重放未确认的
            self._reconcile(server_state, last_processed)

        elif msg["type"] == "entity_state":
            # 其他玩家状态（用于插值）
            pid = msg["player"]
            pos = PlayerState(
                x=msg["x"],
                y=msg["y"],
                timestamp=msg["timestamp"],
            )
            if pid not in self.other_players:
                self.other_players[pid] = (pos, pos)
            else:
                prev, _ = self.other_players[pid]
                self.other_players[pid] = (prev, pos)

    def _reconcile(self, server_state: PlayerState, last_processed_seq: int):
        """和解：校正客户端预测"""
        # 移除已确认的输入
        while self.pending_inputs and self.pending_inputs[0]["seq"] <= last_processed_seq:
            self.pending_inputs.popleft()

        # 重置预测状态为服务器权威位置
        self.predicted.x = server_state.x
        self.predicted.y = server_state.y
        self.predicted.vx = server_state.vx
        self.predicted.vy = server_state.vy
        self.predicted.timestamp = server_state.timestamp

        # 重放未确认的输入
        dt = self.TICK_RATE
        for inp in list(self.pending_inputs):
            self.predicted.x += inp["dx"] * self.MOVE_SPEED * dt
            self.predicted.y += inp["dy"] * self.MOVE_SPEED * dt

    def get_display_position(self) -> tuple[float, float]:
        """获取当前显示位置（客户端预测）"""
        return self.predicted.x, self.predicted.y

    def get_interpolated_other(self, player_id: int) -> tuple[float, float] | None:
        """获取其他玩家插值位置"""
        if player_id not in self.other_players:
            return None
        prev, nxt = self.other_players[player_id]
        if prev.timestamp >= nxt.timestamp:
            return nxt.x, nxt.y

        # 插值
        total = nxt.timestamp - prev.timestamp
        if total <= 0:
            return nxt.x, nxt.y

        render_time = self.sim_time - 0.100  # 渲染 100ms 前的状态
        t = max(0, min(1, (render_time - prev.timestamp) / total))
        x = prev.x + (nxt.x - prev.x) * t
        y = prev.y + (nxt.y - prev.y) * t
        return x, y


# ─── 服务器 ──────────────────────────────────────────────────────
class Server:
    TICK_RATE = 0.033  # ~30fps

    def __init__(self, to_client_A: NetworkSimulator, to_client_B: NetworkSimulator):
        self.to_A = to_client_A
        self.to_B = to_client_B
        self.players: dict[int, PlayerState] = {
            0: PlayerState(timestamp=0),
            1: PlayerState(x=100, y=0, timestamp=0),
        }
        self.sim_time = 0.0

    def receive_and_simulate(self):
        """服务器主循环 — 一帧"""
        self.sim_time += self.TICK_RATE

        # 从两端接收输入
        inputs = []
        # 模拟从客户端 A 的通道接收
        # (在实际代码中，服务器从两个 channel 收消息)
        # 这里简化：统一处理队列
        for msg_list in [self.to_A.receive(), self.to_B.receive()]:
            inputs.extend(msg_list)

        if not inputs:
            return

        # 处理输入
        for msg in inputs:
            pid = msg["player"]
            state = self.players[pid]
            dt = msg.get("dt", self.TICK_RATE)
            state.vx = msg["dx"] * Client.MOVE_SPEED
            state.vy = msg["dy"] * Client.MOVE_SPEED
            state.x += state.vx * dt
            state.y += state.vy * dt
            state.timestamp = self.sim_time

            # 发送权威状态回客户端
            state_msg = {
                "type": "state",
                "player": pid,
                "x": state.x,
                "y": state.y,
                "vx": state.vx,
                "vy": state.vy,
                "timestamp": self.sim_time,
                "last_processed_seq": msg["seq"],
            }
            if pid == 0:
                self.to_A.send(state_msg)
            else:
                self.to_B.send(state_msg)

        # 发送实体状态给对方（用于插值）
        for pid, state in self.players.items():
            entity_msg = {
                "type": "entity_state",
                "player": pid,
                "x": state.x,
                "y": state.y,
                "timestamp": self.sim_time,
            }
            other = 1 if pid == 0 else 0
            if pid == 0:
                self.to_B.send(entity_msg)
            else:
                self.to_A.send(entity_msg)


# ─── 演示 ─────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  网络同步演示：客户端预测 + 服务器和解 + 实体插值")
    print(f"  模拟网络延迟: {NETWORK_DELAY*1000:.0f}ms")
    print("=" * 60)

    # 创建网络通道
    c2s_A = NetworkSimulator()
    s2c_A = NetworkSimulator()
    c2s_B = NetworkSimulator()
    s2c_B = NetworkSimulator()

    # 客户端 A (本地玩家)
    client = Client(0, c2s_A, s2c_A)

    # 服务器 — 从 A 收，从 B 收
    # 把 c2s_A 和 c2s_B 的 receive 传给服务器
    class SimServer:
        def __init__(self):
            self.server = Server(s2c_A, s2c_B)
            self.tick_acc = 0.0
            self.dt = 1.0 / 60

        def run(self):
            self.tick_acc += self.dt
            while self.tick_acc >= self.server.TICK_RATE:
                self.tick_acc -= self.server.TICK_RATE
                # 手动把两个队列的内容喂给服务器
                msgs = c2s_A.receive() + c2s_B.receive()
                if msgs:
                    # 重新入队让服务器处理
                    for m in msgs:
                        self.server.receive_and_simulate()

    sim_server = SimServer()

    # 模拟：玩家 A 向右移动
    print("\n🎮 模拟：玩家 A 按住「→」键向右移动 30 帧")
    print(f"{'帧':>4s}  {'客户端预测位置':>20s}  {'服务器权威位置':>20s}  {'预测误差':>10s}")
    print("-" * 60)

    for frame in range(60):
        # 玩家输入：持续向右
        client.apply_input(1.0, 0.0)

        # 模拟服务器（简化：直接驱动）
        server_msgs = c2s_A.receive()
        srv = Server(s2c_A, s2c_B)
        srv.sim_time = frame * srv.TICK_RATE
        for msg in server_msgs:
            pid = msg["player"]
            state = srv.players[pid]
            state.vx = msg["dx"] * Client.MOVE_SPEED
            state.vy = msg["dy"] * Client.MOVE_SPEED
            state.x += state.vx * Server.TICK_RATE
            state.y += state.vy * Server.TICK_RATE
            state.timestamp = srv.sim_time

            s2c_A.send({
                "type": "state",
                "x": state.x,
                "y": state.y,
                "vx": state.vx,
                "vy": state.vy,
                "timestamp": srv.sim_time,
                "last_processed_seq": msg["seq"],
            })

        # 客户端接收并更新
        client.update()

        # 每 5 帧打印
        if frame % 5 == 0:
            pred_x, pred_y = client.get_display_position()
            svr_x = srv.players[0].x if srv else 0
            error = abs(pred_x - svr_x)
            print(f"{frame:>4d}  ({pred_x:>8.1f}, {pred_y:>6.1f})     ({svr_x:>8.1f}, {srv.players[0].y:>6.1f})     {error:>8.2f}")

    print("-" * 60)
    pred_x, pred_y = client.get_display_position()
    print(f"\n✅ 最终预测位置: ({pred_x:.1f}, {pred_y:.1f})")

    # 演示实体插值
    print(f"\n📦 实体插值演示：")
    print(f"   客户端 B 状态数: {client.other_players}")
    print(f"   当收到其他玩家两次状态后，渲染时在两者间插值，")
    print(f"   保证动作平滑，不受网络抖动影响。")


if __name__ == "__main__":
    main()
