#!/usr/bin/env python3
"""
Socket 房间服务器演示
纯标准库，直接运行。启动服务器后用 nc/telnet 连接。

功能：
  创建/加入/离开房间
  房间内广播消息
  心跳检测（30s 超时断线）

协议（换行分隔文本）：
  CREATE <room_name>     — 创建房间
  JOIN <room_name>       — 加入房间
  LEAVE                  — 离开房间
  SAY <message>          — 发送消息
  LIST                   — 列出所有房间
  WHO                    — 查看当前房间成员
  QUIT                   — 断开连接
"""

import socket
import selectors
import threading
import time
import sys


# ─── 房间模型 ─────────────────────────────────────────────────────
class Room:
    def __init__(self, name: str, owner):
        self.name = name
        self.owner = owner  # 第一个进入的是房主
        self.members: dict[str, "Client"] = {}  # name -> Client

    @property
    def count(self):
        return len(self.members)

    def broadcast(self, sender: "Client", message: str):
        """向房间内所有成员广播消息"""
        for client in self.members.values():
            if client is not sender:
                client.send(f"[{self.name}] {sender.name}: {message}")

    def broadcast_system(self, message: str):
        for client in self.members.values():
            client.send(f"[系统] {message}")


# ─── 客户端连接 ──────────────────────────────────────────────────
class Client:
    def __init__(self, sock: socket.socket, addr):
        self.sock = sock
        self.addr = addr
        self.name = f"Player_{addr[1]}"
        self.room: Room | None = None
        self.last_heartbeat = time.time()

    def send(self, message: str):
        """发送一行消息"""
        try:
            self.sock.sendall(f"{message}\n".encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ─── 服务器 ──────────────────────────────────────────────────────
class GameServer:
    HEARTBEAT_INTERVAL = 10   # 每10秒发送心跳
    HEARTBEAT_TIMEOUT = 30    # 30秒无心跳断线

    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.rooms: dict[str, Room] = {}
        self.clients: dict[socket.socket, Client] = {}
        self.selector = selectors.DefaultSelector()
        self.running = True

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(128)
        server.setblocking(False)
        self.selector.register(server, selectors.EVENT_READ, data=None)

        print(f"🎮 游戏房间服务器已启动: {self.host}:{self.port}")
        print(f"   连接方式: nc {self.host} {self.port}")
        print(f"   可用命令: CREATE/JOIN/LEAVE/SAY/LIST/WHO/QUIT")

        # 心跳线程
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

        try:
            while self.running:
                events = self.selector.select(timeout=1.0)
                for key, mask in events:
                    if key.data is None:
                        self._accept(key.fileobj)
                    else:
                        self._handle(key.fileobj, key.data)
        except KeyboardInterrupt:
            print("\n服务器关闭中...")
        finally:
            self.shutdown()

    def _accept(self, server: socket.socket):
        conn, addr = server.accept()
        conn.setblocking(False)
        client = Client(conn, addr)
        self.clients[conn] = client
        self.selector.register(conn, selectors.EVENT_READ, data=client)
        client.send(f"🎮 欢迎, {client.name}! 输入命令 (LIST 查看房间)")
        print(f"[+] {client.name} 已连接 ({addr})")

    def _handle(self, conn: socket.socket, client: Client):
        try:
            data = conn.recv(4096)
        except ConnectionResetError:
            self._disconnect(conn, client)
            return

        if not data:
            self._disconnect(conn, client)
            return

        client.last_heartbeat = time.time()
        for line in data.decode("utf-8", errors="ignore").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            self._process_command(client, line)

    def _process_command(self, client: Client, line: str):
        parts = line.split(maxsplit=1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "CREATE":
            self._cmd_create(client, arg)
        elif cmd == "JOIN":
            self._cmd_join(client, arg)
        elif cmd == "LEAVE":
            self._cmd_leave(client)
        elif cmd == "SAY":
            self._cmd_say(client, arg)
        elif cmd == "LIST":
            self._cmd_list(client)
        elif cmd == "WHO":
            self._cmd_who(client)
        elif cmd == "QUIT":
            self._disconnect(client.sock, client)
        else:
            client.send(f"未知命令: {cmd}")

    def _cmd_create(self, client: Client, room_name: str):
        if not room_name:
            client.send("用法: CREATE <房间名>")
            return
        if room_name in self.rooms:
            client.send(f"房间 '{room_name}' 已存在")
            return
        if client.room:
            self._cmd_leave(client)

        room = Room(room_name, client)
        self.rooms[room_name] = room
        room.members[client.name] = client
        client.room = room
        client.send(f"✅ 创建并加入房间: {room_name}")
        print(f"[房] {client.name} 创建了房间 '{room_name}'")

    def _cmd_join(self, client: Client, room_name: str):
        if not room_name:
            client.send("用法: JOIN <房间名>")
            return
        room = self.rooms.get(room_name)
        if not room:
            client.send(f"房间 '{room_name}' 不存在")
            return
        if client.room == room:
            client.send("已在该房间中")
            return
        if client.room:
            self._cmd_leave(client)

        room.members[client.name] = client
        client.room = room
        room.broadcast_system(f"{client.name} 加入了房间")
        client.send(f"✅ 加入房间: {room_name} ({room.count}人)")
        print(f"[房] {client.name} 加入了 '{room_name}'")

    def _cmd_leave(self, client: Client):
        room = client.room
        if not room:
            client.send("你不在任何房间中")
            return
        del room.members[client.name]
        client.room = None
        client.send(f"已离开房间: {room.name}")

        if room.count == 0:
            del self.rooms[room.name]
            print(f"[房] 房间 '{room.name}' 已解散")
        else:
            room.broadcast_system(f"{client.name} 离开了房间")

    def _cmd_say(self, client: Client, message: str):
        if not client.room:
            client.send("你不在房间中")
            return
        if not message:
            client.send("用法: SAY <消息>")
            return
        client.room.broadcast(client, message)

    def _cmd_list(self, client: Client):
        if not self.rooms:
            client.send("暂无房间")
            return
        lines = ["┌──── 房间列表 ────┐"]
        for room in self.rooms.values():
            lines.append(f"│ {room.name:<20s} ({room.count}人) │")
        lines.append("└──────────────────┘")
        client.send("\n".join(lines))

    def _cmd_who(self, client: Client):
        if not client.room:
            client.send("你不在房间中")
            return
        room = client.room
        lines = [f"┌─ {room.name} ({room.count}人) ─┐"]
        for i, name in enumerate(room.members, 1):
            marker = "★" if room.members[name] is room.owner else "  "
            lines.append(f"│ {marker} {name:<20s} │")
        lines.append("└─────────────────────┘")
        client.send("\n".join(lines))

    def _disconnect(self, conn: socket.socket, client: Client):
        print(f"[-] {client.name} 断开连接")
        if client.room:
            self._cmd_leave(client)
        self.selector.unregister(conn)
        del self.clients[conn]
        client.close()

    def _heartbeat_loop(self):
        """定期检查心跳"""
        while self.running:
            time.sleep(self.HEARTBEAT_INTERVAL)
            now = time.time()
            disconnected = []
            for conn, client in list(self.clients.items()):
                if now - client.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                    disconnected.append((conn, client))

            for conn, client in disconnected:
                client.send("⏰ 心跳超时，已断开")
                self._disconnect(conn, client)

            if disconnected:
                print(f"[心跳] 踢出 {len(disconnected)} 个超时客户端")

    def shutdown(self):
        self.running = False
        for conn in list(self.clients):
            self.clients[conn].close()
        self.selector.close()
        print("服务器已关闭")


# ─── 测试客户端（用于演示）───────────────────────────────────────
def test_clients():
    """启动两个模拟客户端进行演示"""
    import time
    time.sleep(0.5)

    def client_worker(name, commands):
        time.sleep(0.2)  # 等待服务器就绪
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 9000))
        sock.settimeout(2)

        def recv_all():
            try:
                return sock.recv(4096).decode("utf-8", errors="ignore")
            except socket.timeout:
                return ""

        # 接收欢迎消息
        data = recv_all()
        print(f"[{name}] 收到: {data.strip()}")

        for cmd in commands:
            print(f"[{name}] >>> {cmd}")
            sock.sendall(f"{cmd}\n".encode("utf-8"))
            time.sleep(0.3)
            resp = recv_all()
            if resp:
                print(f"[{name}] <<< {resp.strip()}")

        sock.close()

    # 客户端 A：创建房间
    threading.Thread(target=client_worker, args=("Alice", [
        "CREATE 冒险大厅",
        "SAY 大家好！",
        "WHO",
    ]), daemon=True).start()

    # 客户端 B：加入房间
    threading.Thread(target=client_worker, args=("Bob", [
        "LIST",
        "JOIN 冒险大厅",
        "WHO",
        "SAY 我来啦！",
        "LEAVE",
        "QUIT",
    ]), daemon=True).start()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        # 启动服务器 + 模拟客户端
        server = GameServer("127.0.0.1", 9000)
        test_clients()
        server.start()
    else:
        GameServer().start()
