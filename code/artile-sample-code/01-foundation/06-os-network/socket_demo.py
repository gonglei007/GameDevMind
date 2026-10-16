#!/usr/bin/env python3
"""Real loopback correctness examples; deterministic faults, not Internet benchmarks."""
from pathlib import Path
import math
import queue
import socket
import struct
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '02-technical' / '05-networking'))
from net_demo import FrameDecoder, ProtocolError, encode_frame


def tcp_roundtrip(messages):
    """Echo framed bytes. Echo proves this handler ran, not any business transaction."""
    failures = queue.Queue()
    with socket.socket() as listener:
        listener.settimeout(3)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)

        def serve():
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(3)
                    decoder = FrameDecoder()
                    while True:
                        chunk = peer.recv(4096)
                        if not chunk:
                            decoder.finish()
                            break
                        for payload in decoder.feed(chunk):
                            peer.sendall(encode_frame(payload))
            except Exception as error:
                failures.put(error)

        worker = threading.Thread(target=serve)
        worker.start()
        received = []
        try:
            with socket.create_connection(listener.getsockname(), timeout=3) as client:
                wire = b''.join(encode_frame(m) for m in messages)
                # Deliberately split headers and UTF-8 across writes. TCP can regroup these.
                for offset in range(0, len(wire), 3):
                    client.sendall(wire[offset:offset + 3])
                client.shutdown(socket.SHUT_WR)
                decoder = FrameDecoder()
                while True:
                    chunk = client.recv(7)
                    if not chunk:
                        decoder.finish()
                        break
                    received.extend(decoder.feed(chunk))
        finally:
            worker.join(4)
        if worker.is_alive():
            raise TimeoutError('TCP worker did not terminate')
        if not failures.empty():
            raise failures.get()
        return received


def encode_position(sequence, x, y, z):
    if type(sequence) is not int or not 1 <= sequence <= 0xffffffff:
        raise ProtocolError('invalid UDP sequence (no wrap in this demo)')
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ProtocolError('nonfinite position')
    try:
        return struct.pack('!Ifff', sequence, x, y, z)
    except (OverflowError, struct.error) as error:
        raise ProtocolError('position outside float32 range') from error


class LatestPosition:
    """Only for replaceable snapshots; duplicate/older datagrams do not rewind state."""
    def __init__(self):
        self.sequence = 0
        self.position = None

    def receive(self, raw):
        if len(raw) != 16:
            raise ProtocolError('position datagram must be exactly 16 bytes')
        seq, x, y, z = struct.unpack('!Ifff', raw)
        if seq == 0 or not all(math.isfinite(v) for v in (x, y, z)):
            raise ProtocolError('invalid position datagram')
        if seq <= self.sequence:
            return False
        self.sequence, self.position = seq, (x, y, z)
        return True


def udp_roundtrip():
    state = LatestPosition()
    adopted = []
    # 3 and 6 intentionally omitted; 5 duplicated and 4 delivered after 5.
    # No random loss claims: this is deterministic application-level injection.
    order = [1, 2, 5, 5, 4, 7, 8]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM) as sender:
        receiver.settimeout(3)
        receiver.bind(('127.0.0.1', 0))
        sender.bind(('127.0.0.1', 0))
        for seq in order:
            sender.sendto(encode_position(seq, float(seq), 0, 0), receiver.getsockname())
            raw, address = receiver.recvfrom(1024)
            if address != sender.getsockname():
                raise ProtocolError('unexpected source')
            if state.receive(raw):
                adopted.append(state.sequence)
    return adopted, state


def main():
    messages = ['登录'.encode(), b'chat\x00payload', b'x' * 8192]
    assert tcp_roundtrip(messages) == messages
    adopted, state = udp_roundtrip()
    assert adopted == [1, 2, 5, 7, 8] and state.sequence == 8
    print('TCP: framed loopback echo exact; no business commit guarantee')
    print('UDP: injected omission/duplicate/reorder; latest snapshot preserved')
    print('No TLS, authentication, congestion control, weak-network or capacity benchmark')


if __name__ == '__main__':
    main()
