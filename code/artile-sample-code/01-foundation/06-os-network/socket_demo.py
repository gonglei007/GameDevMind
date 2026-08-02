#!/usr/bin/env python3
"""
TCP vs UDP 游戏场景演示

对应文章：../../游戏开发图谱/基础能力篇/一-06-游戏开发者应知的操作系统和网络基础.md

模拟两个典型游戏网络场景：
  1. TCP 可靠传输 —— 适合：登录、交易、聊天。保证顺序、不丢包。
  2. UDP 丢包容忍 —— 适合：位置同步、射击命中。低延迟，容忍丢包。

实现：
  - TCP echo 服务器 + 客户端（模拟可靠 RPC）
  - UDP 位置同步模拟（模拟高频快照，演示丢包时的表现）
  - 丢包率可配置，展示 UDP 的"尽力而为"特性

纯标准库：socket + threading，无外部依赖。
"""

import socket
import threading
import time
import random
import struct
import sys


# ═══════════════════════════════════════════════════════════════════════════════
# TCP 部分：可靠传输 —— 模拟登录/交易/聊天
# ═══════════════════════════════════════════════════════════════════════════════

def tcp_server(host: str, port: int, ready_event: threading.Event):
    """TCP Echo 服务器。接收消息后返回 ACK。模拟可靠 RPC。"""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(1)
    server_sock.settimeout(3.0)

    ready_event.set()  # 通知主线程服务器已就绪
    print(f"  [TCP Server] 监听 {host}:{port}")

    try:
        conn, addr = server_sock.accept()
        print(f"  [TCP Server] 客户端连接: {addr}")

        with conn:
            conn.settimeout(3.0)
            for seq in range(1, 6):
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    msg = data.decode()
                    print(f"  [TCP Server] 收到 #{seq}: {msg}")
                    # 模拟处理延迟
                    time.sleep(0.05)
                    ack = f"ACK:{msg}"
                    conn.sendall(ack.encode())
                    print(f"  [TCP Server] 发送 ACK: {ack}")
                except socket.timeout:
                    print(f"  [TCP Server] 超时，等待 #{seq}")
                    break
    except socket.timeout:
        print("  [TCP Server] 等待连接超时")
    finally:
        server_sock.close()
        print("  [TCP Server] 关闭")


def tcp_client(host: str, port: int, ready_event: threading.Event):
    """TCP 客户端。发送有序消息并等待 ACK。"""
    ready_event.wait()  # 等待服务器就绪
    time.sleep(0.1)     # 给 accept 一点时间

    print(f"\n  [TCP Client] 连接 {host}:{port}")
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.settimeout(3.0)

    try:
        client_sock.connect((host, port))
        print("  [TCP Client] 连接成功 ✓")

        messages = ["LOGIN user=hero", "MOVE x=10 y=20", "ATTACK target=orc",
                     "USE_ITEM id=42", "LOGOUT"]
        for seq, msg in enumerate(messages, 1):
            print(f"  [TCP Client] 发送 #{seq}: {msg}")
            client_sock.sendall(msg.encode())
            # 等待 ACK（TCP 保证送达）
            ack = client_sock.recv(1024).decode()
            print(f"  [TCP Client] 收到 #{seq}: {ack} ✓")

        print("  [TCP Client] 全部消息确认 ✓")
    except (ConnectionRefusedError, socket.timeout) as e:
        print(f"  [TCP Client] 错误: {e}")
    finally:
        client_sock.close()


# ═══════════════════════════════════════════════════════════════════════════════
# UDP 部分：丢包容忍 —— 模拟位置同步
# ═══════════════════════════════════════════════════════════════════════════════

def udp_server(host: str, port: int, ready_event: threading.Event,
               packet_loss_rate: float = 0.0):
    """
    UDP 服务器。接收玩家位置快照。
    
    在真实游戏中，UDP 服务器不保证送达，丢包由客户端插值/外推补偿。
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((host, port))
    server_sock.settimeout(0.5)

    ready_event.set()
    print(f"\n  [UDP Server] 监听 {host}:{port}, 丢包率模拟={packet_loss_rate:.0%}")

    received = 0
    expected = 20
    last_seq = 0
    gaps = []

    try:
        for _ in range(expected + 10):
            try:
                data, addr = server_sock.recvfrom(1024)
                # 解析：seq(4bytes) + x(4bytes) + y(4bytes) + z(4bytes)
                seq, x, y, z = struct.unpack("!i f f f", data)
                received += 1

                if seq != last_seq + 1:
                    gaps.append((last_seq + 1, seq - 1))
                    print(f"  [UDP Server] ⚠ 检测到丢包: seq {last_seq+1}~{seq-1}")

                last_seq = seq
                if seq % 5 == 0:
                    print(f"  [UDP Server] 收到 seq={seq}: pos=({x:.1f},{y:.1f},{z:.1f})")
            except socket.timeout:
                break
    finally:
        server_sock.close()
        loss_pct = (1 - received / expected) * 100 if expected > 0 else 0
        print(f"  [UDP Server] 关闭. 收到 {received}/{expected} 包, "
              f"丢包率 ≈ {loss_pct:.1f}%")
        if gaps:
            print(f"  [UDP Server] 丢包区间: {gaps}")


def udp_client(host: str, port: int, ready_event: threading.Event):
    """
    UDP 客户端。高频发送位置快照 (seq, x, y, z)。
    
    真实场景：60Hz 位置同步 → 每秒 60 个包，每包约 20 bytes。
    """
    ready_event.wait()
    time.sleep(0.05)

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"  [UDP Client] 开始发送位置快照 → {host}:{port}")

    x, y, z = 0.0, 0.0, 0.0
    sent = 0

    for seq in range(1, 21):
        # 模拟玩家移动
        x += 0.5
        y += 0.3
        z = 1.5 + 0.1 * math_sin(seq * 0.5)

        # 打包：序列号 + 位置
        data = struct.pack("!i f f f", seq, x, y, z)
        client_sock.sendto(data, (host, port))
        sent += 1

        if seq % 5 == 0:
            print(f"  [UDP Client] 发送 seq={seq}: pos=({x:.1f},{y:.1f},{z:.1f})")

        # 模拟 60Hz 发送频率 (~16ms 间隔，这里加快演示)
        time.sleep(0.03)

    client_sock.close()
    print(f"  [UDP Client] 发送完毕，共 {sent} 包 (不保证送达)")


def math_sin(x: float) -> float:
    """本地 sin 别名，避免额外 import。"""
    import math
    return math.sin(x)


# ═══════════════════════════════════════════════════════════════════════════════
# UDP 丢包模拟服务器（手动丢包）
# ═══════════════════════════════════════════════════════════════════════════════

def udp_server_with_loss(
    host: str, port: int, ready_event: threading.Event, loss_rate: float = 0.3
):
    """
    UDP 服务器 —— 主动丢弃一部分包，模拟真实网络丢包。

    展示 UDP 的核心特性：
      1. 不保证送达
      2. 不保证顺序（虽然本 demo 不模拟乱序）
      3. 无连接，无重传
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((host, port))
    server_sock.settimeout(0.5)

    ready_event.set()
    print(f"\n  [UDP-Loss Server] 监听 {host}:{port}, 主动丢包率={loss_rate:.0%}")

    received = 0
    dropped = 0
    expected = 20

    try:
        for _ in range(expected + 10):
            try:
                data, addr = server_sock.recvfrom(1024)
                seq, x, y, z = struct.unpack("!i f f f", data)

                # 模拟丢包
                if random.random() < loss_rate:
                    dropped += 1
                    if seq % 5 == 0:
                        print(f"  [UDP-Loss Server] ✗ 主动丢弃 seq={seq}")
                    continue

                received += 1
                if seq % 5 == 0 or received <= 3:
                    print(f"  [UDP-Loss Server] ✓ 处理 seq={seq}: "
                          f"pos=({x:.1f},{y:.1f},{z:.1f})")
            except socket.timeout:
                break
    finally:
        server_sock.close()
        print(f"  [UDP-Loss Server] 关闭. 收到 {received}, 主动丢弃 {dropped}, "
              f"总计 {received + dropped}/{expected}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main 演示
# ═══════════════════════════════════════════════════════════════════════════════

def run_tcp_demo():
    """演示 TCP 可靠传输。"""
    print("=" * 60)
    print("  场景 1: TCP 可靠传输（模拟登录/交易/聊天）")
    print("=" * 60)
    print()

    host = "127.0.0.1"
    port = 9001
    ready = threading.Event()

    server_thread = threading.Thread(
        target=tcp_server, args=(host, port, ready), daemon=True
    )
    server_thread.start()

    tcp_client(host, port, ready)
    server_thread.join(timeout=5)

    print("\n  → TCP 结论：所有消息按序送达，每条都有 ACK 确认。")
    print("            适合：登录、交易、聊天等必须可靠送达的场景。")


def run_udp_demo(loss_rate: float):
    """演示 UDP 丢包容忍。"""
    if loss_rate > 0:
        print("\n" + "=" * 60)
        print(f"  场景 2: UDP 丢包容忍（模拟位置同步, 丢包率={loss_rate:.0%})")
    else:
        print("\n" + "=" * 60)
        print("  场景 2: UDP 完美网络（模拟位置同步, 无丢包）")
    print("=" * 60)
    print()

    host = "127.0.0.1"
    port = 9002
    ready = threading.Event()

    if loss_rate > 0:
        server_thread = threading.Thread(
            target=udp_server_with_loss,
            args=(host, port, ready, loss_rate),
            daemon=True,
        )
    else:
        server_thread = threading.Thread(
            target=udp_server,
            args=(host, port, ready, 0.0),
            daemon=True,
        )
    server_thread.start()

    udp_client(host, port, ready)
    server_thread.join(timeout=5)

    print()
    print("  → UDP 结论：低延迟但不可靠。丢包时游戏用插值/外推补偿。")
    print("            适合：位置同步、射击命中、语音通话等实时场景。")


def run_comparison():
    """对比总结。"""
    print("\n" + "=" * 60)
    print("  TCP vs UDP 游戏场景总结")
    print("=" * 60)
    print("""
  ┌──────────────┬─────────────────────┬─────────────────────┐
  │   特性        │   TCP               │   UDP               │
  ├──────────────┼─────────────────────┼─────────────────────┤
  │ 连接         │ 面向连接 (三次握手) │ 无连接              │
  │ 可靠性       │ 保证送达, 有序      │ 不保证, 尽力而为    │
  │ 延迟         │ 较高 (重传等待)     │ 低                  │
  │ 头部开销     │ 20 bytes            │ 8 bytes             │
  │ 流控/拥塞控制│ 有 (滑动窗口)       │ 无 (需应用层实现)   │
  │ 适用游戏场景 │ 登录, 交易, 聊天    │ 位置同步, 射击, VoIP │
  └──────────────┴─────────────────────┴─────────────────────┘

  现代游戏引擎通常 TCP + UDP 混合使用：
  - TCP 通道：关键状态变更（登录、购买、任务完成）
  - UDP 通道：高频状态同步（移动、旋转、动画状态）
  - 部分引擎（如 UE）还使用基于 UDP 的可靠层（如 ENet、KCP）
""")


def main():
    print("=" * 60)
    print("  TCP vs UDP 游戏网络通信演示")
    print("=" * 60)

    # 1. TCP 可靠传输
    run_tcp_demo()

    # 2. UDP 无丢包（理想网络）
    run_udp_demo(loss_rate=0.0)

    # 3. UDP 有丢包（真实网络模拟）
    run_udp_demo(loss_rate=0.3)

    # 4. 总结
    run_comparison()


if __name__ == "__main__":
    main()
