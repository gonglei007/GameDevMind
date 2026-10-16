#!/usr/bin/env python3
"""有界协议教学：带类型序列化、TCP 帧、写缓冲、心跳与输入确认。

纯标准库。运行 python net_demo.py；真实 Socket 回环见 socket_demo.py。
"""
from collections import deque
from dataclasses import dataclass
import json
import math
import struct
import time

MAX_FRAME = 65536


class ProtocolError(ValueError):
    pass


class ResyncRequired(ProtocolError):
    pass


def _utf8(value):
    try:
        return value.encode('utf-8')
    except UnicodeError as error:
        raise ProtocolError("invalid Unicode string") from error


def _validate_message(msg_type, data):
    if type(msg_type) is not int or not 0 <= msg_type <= 255 or type(data) is not dict or len(data) > 64:
        raise ProtocolError("invalid message envelope")
    for key, value in data.items():
        if not isinstance(key, str) or not 1 <= len(_utf8(key)) <= 255:
            raise ProtocolError("invalid key")
        if type(value) is int and -(1 << 63) <= value < (1 << 63):
            continue
        if type(value) is float and math.isfinite(value):
            continue
        if type(value) is str and len(_utf8(value)) <= 4096:
            continue
        raise ProtocolError("unsupported or out-of-range value")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate JSON key")
        result[key] = value
    return result


class MessageSerializer:
    """Fixed teaching format: GN/version=1, type:u8, count:u16, tagged values.

    Key: u8 byte length + UTF-8; values: 1=int64, 2=float64, 3=u16 length + UTF-8.
    Not a replacement for a versioned production schema/Protobuf.
    """
    @staticmethod
    def to_json(msg_type, data):
        _validate_message(msg_type, data)
        raw = json.dumps({'t': msg_type, 'd': data}, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
        if len(raw) > MAX_FRAME:
            raise ProtocolError("message too large")
        return raw

    @staticmethod
    def from_json(raw):
        if not 0 < len(raw) <= MAX_FRAME:
            raise ProtocolError("invalid JSON length")
        try:
            obj = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object)
            if type(obj) is not dict or set(obj) != {'t', 'd'}:
                raise ProtocolError("invalid JSON envelope")
            _validate_message(obj['t'], obj['d'])
            return obj['t'], obj['d']
        except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
            raise ProtocolError("invalid JSON") from error

    @staticmethod
    def to_binary(msg_type, data):
        _validate_message(msg_type, data)
        buf = bytearray(b'GN\x01' + struct.pack('!BH', msg_type, len(data)))
        for key, value in data.items():
            encoded = key.encode('utf-8')
            buf.extend(bytes([len(encoded)]) + encoded)
            if type(value) is int:
                buf.extend(b'\x01' + struct.pack('!q', value))
            elif type(value) is float:
                buf.extend(b'\x02' + struct.pack('!d', value))
            else:
                encoded = value.encode('utf-8')
                buf.extend(b'\x03' + struct.pack('!H', len(encoded)) + encoded)
        if len(buf) > MAX_FRAME:
            raise ProtocolError("message too large")
        return bytes(buf)

    @staticmethod
    def from_binary(raw):
        if not 6 <= len(raw) <= MAX_FRAME or raw[:3] != b'GN\x01':
            raise ProtocolError("invalid binary envelope/version")
        offset = 3

        def take(size):
            nonlocal offset
            if offset + size > len(raw):
                raise ProtocolError("truncated binary value")
            result = raw[offset:offset + size]
            offset += size
            return result

        msg_type, count = struct.unpack('!BH', take(3))
        if count > 64:
            raise ProtocolError("too many fields")
        result = {}
        try:
            for _ in range(count):
                key = take(take(1)[0]).decode('utf-8')
                if not key or key in result:
                    raise ProtocolError("empty or duplicate key")
                tag = take(1)[0]
                if tag == 1:
                    value = struct.unpack('!q', take(8))[0]
                elif tag == 2:
                    value = struct.unpack('!d', take(8))[0]
                elif tag == 3:
                    size = struct.unpack('!H', take(2))[0]
                    if size > 4096:
                        raise ProtocolError("string too long")
                    value = take(size).decode('utf-8')
                else:
                    raise ProtocolError("unknown value tag")
                result[key] = value
        except UnicodeError as error:
            raise ProtocolError("invalid UTF-8") from error
        if offset != len(raw):
            raise ProtocolError("trailing bytes")
        _validate_message(msg_type, result)
        return msg_type, result


def encode_frame(payload):
    if not 1 <= len(payload) <= MAX_FRAME:
        raise ProtocolError("invalid frame length")
    return struct.pack('!I', len(payload)) + payload


class FrameDecoder:
    """Incremental u32 length framing; recv chunks are capped separately from frames."""
    def __init__(self):
        self.buffer = bytearray()
        self.expected = None
        self.closed = False

    def feed(self, chunk):
        if self.closed:
            raise ProtocolError("decoder closed")
        if len(chunk) > MAX_FRAME + 4:
            self.closed = True
            raise ProtocolError("read chunk exceeds budget")
        frames = []
        offset = 0
        while offset < len(chunk):
            target = 4 if self.expected is None else self.expected
            count = min(target - len(self.buffer), len(chunk) - offset)
            self.buffer.extend(chunk[offset:offset + count])
            offset += count
            if len(self.buffer) < target:
                continue
            if self.expected is None:
                self.expected = struct.unpack('!I', self.buffer)[0]
                self.buffer.clear()
                if not 1 <= self.expected <= MAX_FRAME:
                    self.closed = True
                    raise ProtocolError("advertised frame length exceeds policy")
            else:
                frames.append(bytes(self.buffer))
                self.buffer.clear()
                self.expected = None
        return frames

    def finish(self):
        self.closed = True
        if self.buffer or self.expected is not None:
            raise ProtocolError("EOF inside a frame")


class SendBuffer:
    """Bounded nonblocking write queue. flush_once preserves unsent bytes on partial writes."""
    def __init__(self, budget=2 * (MAX_FRAME + 4)):
        self.budget, self.queued = budget, 0
        self.parts = deque()

    def enqueue(self, payload):
        frame = encode_frame(payload)
        if self.queued + len(frame) > self.budget:
            raise BufferError("slow reader: outbound budget exceeded")
        self.parts.append(frame)
        self.queued += len(frame)

    def flush_once(self, send):
        if not self.parts:
            return
        head = self.parts[0]
        try:
            written = send(head)
        except BlockingIOError:
            return
        if written == 0:
            raise EOFError("peer closed while writing")
        if not 0 < written <= len(head):
            raise RuntimeError("invalid send result")
        self.queued -= written
        self.parts.popleft()
        if written < len(head):
            self.parts.appendleft(head[written:])


class HeartbeatManager:
    """Elapsed-time watchdog with one outstanding, session-scoped probe; no polling counter."""
    def __init__(self, generation='demo-session', interval=2.0, timeout=6.0, start=None):
        if not 0 < interval < timeout or not math.isfinite(timeout):
            raise ValueError("invalid heartbeat budget")
        start = time.monotonic() if start is None else start
        if not math.isfinite(start):
            raise ValueError("invalid clock origin")
        self.generation, self.interval, self.timeout = generation, interval, timeout
        self.last_send = self.last_progress = self.last_now = start
        self.connected, self.pending, self.sequence = True, None, 0

    def check_timeout(self, now):
        if not math.isfinite(now) or now < self.last_now:
            raise ValueError("use a monotonic clock")
        self.last_now = now
        expired = self.connected and now - self.last_progress >= self.timeout
        if expired:
            self.connected = False
        return expired

    def send_heartbeat(self, now):
        self.check_timeout(now)
        if not self.connected or now - self.last_send < self.interval:
            return None
        self.last_send = now
        if self.pending is None:
            self.sequence += 1
            self.pending = (self.generation, self.sequence)
        return self.pending

    def receive_heartbeat(self, token, now):
        self.check_timeout(now)
        if not self.connected or self.pending is None or token != self.pending:
            return False
        self.last_progress, self.pending = now, None
        return True


@dataclass(frozen=True)
class Input:
    seq: int
    dt: float
    dx: float
    dy: float


@dataclass(frozen=True)
class Snapshot:
    sequence: int
    acknowledged_input: int
    x: float
    y: float


class StateSyncDemo:
    """Local toy model: reliable ordered input prefix, no actual sockets or physics."""
    def __init__(self, pending_limit=32):
        self.next_input, self.server_ack = 1, 0
        self.snapshot_sequence, self.last_snapshot, self.last_ack = 0, 0, 0
        self.client_position = self.server_position = (0.0, 0.0)
        self.pending_inputs, self.pending_limit = deque(), pending_limit

    @staticmethod
    def _advance(position, command):
        if not (math.isfinite(command.dt) and 0 < command.dt <= 0.25 and
                all(math.isfinite(v) and abs(v) <= 1 for v in (command.dx, command.dy))):
            raise ProtocolError("invalid simulation input")
        return position[0] + command.dx * command.dt, position[1] + command.dy * command.dt

    def client_tick(self, dt, input_dx, input_dy):
        if len(self.pending_inputs) >= self.pending_limit:
            raise ResyncRequired("pending budget exhausted; do not silently discard inputs")
        command = Input(self.next_input, dt, input_dx, input_dy)
        position = self._advance(self.client_position, command)
        self.pending_inputs.append(command)
        self.next_input += 1
        self.client_position = position
        return command

    def server_receive_input(self, command):
        if type(command.seq) is not int or command.seq < 1:
            raise ProtocolError("invalid input sequence")
        if command.seq <= self.server_ack:
            return False
        if command.seq != self.server_ack + 1:
            raise ResyncRequired("input gap requires recovery")
        self.server_position = self._advance(self.server_position, command)
        self.server_ack = command.seq
        return True

    def server_snapshot(self):
        self.snapshot_sequence += 1
        return Snapshot(self.snapshot_sequence, self.server_ack, *self.server_position)

    def reconcile(self, snapshot):
        if (type(snapshot.sequence) is not int or snapshot.sequence < 1 or
                type(snapshot.acknowledged_input) is not int or snapshot.acknowledged_input < 0):
            raise ProtocolError("invalid snapshot sequence")
        if snapshot.sequence <= self.last_snapshot or snapshot.acknowledged_input < self.last_ack:
            return False
        if not self.last_ack <= snapshot.acknowledged_input < self.next_input or not all(
                math.isfinite(v) for v in (snapshot.x, snapshot.y)):
            raise ProtocolError("invalid authority acknowledgement/state")
        remaining = deque(c for c in self.pending_inputs if c.seq > snapshot.acknowledged_input)
        rebuilt = (snapshot.x, snapshot.y)
        for command in remaining:
            rebuilt = self._advance(rebuilt, command)
        self.pending_inputs = remaining
        self.client_position = rebuilt
        self.last_snapshot, self.last_ack = snapshot.sequence, snapshot.acknowledged_input
        return True


def main():
    data = {'x': 1.5, 'hp': 100, 'name': '玩家'}
    for encode, decode in [(MessageSerializer.to_json, MessageSerializer.from_json),
                           (MessageSerializer.to_binary, MessageSerializer.from_binary)]:
        raw = encode(1, data)
        assert decode(raw) == (1, data)
        print(f'{encode.__name__}: {len(raw)} bytes, round trip OK (not a benchmark)')
    hb = HeartbeatManager(start=0)
    token = hb.send_heartbeat(2)
    assert hb.receive_heartbeat(token, 3)
    assert hb.check_timeout(9)
    print('heartbeat: elapsed deadline reached; a new connection needs a new session')
    sync = StateSyncDemo()
    commands = [sync.client_tick(dt, dx, dy) for dt, dx, dy in [(0.1, 1, 0), (0.2, 0, 1), (0.05, 0, 0)]]
    for command in commands:
        sync.server_receive_input(command)
        sync.reconcile(sync.server_snapshot())
    assert sync.client_position == sync.server_position and not sync.pending_inputs
    print('reconciliation: acknowledged prefix drained; final positions match')


if __name__ == '__main__':
    main()
