import struct
import unittest
from net_demo import (MAX_FRAME, ProtocolError, ResyncRequired, MessageSerializer as S,
                      FrameDecoder, SendBuffer, encode_frame, HeartbeatManager, StateSyncDemo, Input, Snapshot)


class SerializationTests(unittest.TestCase):
    def test_roundtrip_types(self):
        values = {'hp': 100, 'low': -(1 << 63), 'high': (1 << 63) - 1, 'x': 1.5, 'name': '玩家😀'}
        for encode, decode in [(S.to_json, S.from_json), (S.to_binary, S.from_binary)]:
            result = decode(encode(255, values))
            self.assertEqual(result, (255, values))
            for key in values:
                self.assertIs(type(result[1][key]), type(values[key]))

    def test_unsupported_values(self):
        for value in [True, None, [], {}, 1 << 63, float('nan'), float('inf'), 'x' * 4097, '\ud800']:
            for encode in [S.to_json, S.to_binary]:
                with self.assertRaises(ProtocolError):
                    encode(1, {'v': value})
        for kind, data in [(-1, {}), (256, {}), (True, {}), (1, {'': 1}), (1, {'x' * 256: 1})]:
            with self.assertRaises(ProtocolError):
                S.to_binary(kind, data)

    def test_binary_rejects_every_truncation(self):
        raw = S.to_binary(1, {'a': 3, 'b': 1.5, 'c': '中文'})
        for end in range(len(raw)):
            with self.assertRaises(ProtocolError):
                S.from_binary(raw[:end])
        single = S.to_binary(1, {'a': 3})
        for bad in [raw + b'x', b'GN\x02' + raw[3:], b'GN\x01\x01\x00\x01\x01a\xff',
                    b'GN\x01\x01\x00\x02' + single[6:] * 2,
                    b'GN\x01\x01\x00\x01\x01\xff\x01' + struct.pack('!q', 1),
                    b'GN\x01\x01\x00\x01\x01a\x02' + struct.pack('!d', float('nan'))]:
            with self.assertRaises(ProtocolError):
                S.from_binary(bad)

    def test_json_invalid(self):
        for raw in [b'', b'[]', b'{"t":1,"d":{},"t":2}', b'{"t":1,"d":{"v":NaN}}',
                    b'{"t":1,"d":{"a":1,"a":2}}', b'\xff', b'{"t":1,"d":{},"extra":0}',
                    b'[' * 2000 + b']' * 2000, b'{"t":1,"d":{"v":"\\ud800"}}', b'x' * (MAX_FRAME + 1)]:
            with self.assertRaises(ProtocolError):
                S.from_json(raw)


class FramingTests(unittest.TestCase):
    def test_every_split_and_coalescing(self):
        payloads = ['多字节😀'.encode(), b'x', b'abc\x00def']
        wire = b''.join(map(encode_frame, payloads))
        for split in range(len(wire) + 1):
            decoder = FrameDecoder()
            self.assertEqual(decoder.feed(wire[:split]) + decoder.feed(wire[split:]), payloads)
            decoder.finish()
        decoder = FrameDecoder()
        result = []
        for byte in wire:
            result.extend(decoder.feed(bytes([byte])))
        self.assertEqual(result, payloads)
        decoder.finish()

    def test_bounds_and_eof(self):
        decoder = FrameDecoder()
        self.assertEqual(decoder.feed(encode_frame(b'x' * MAX_FRAME)), [b'x' * MAX_FRAME])
        decoder.finish()
        for raw in [struct.pack('!I', 0), struct.pack('!I', MAX_FRAME + 1), b'x' * (MAX_FRAME + 5)]:
            decoder = FrameDecoder()
            with self.assertRaises(ProtocolError):
                decoder.feed(raw)
            with self.assertRaises(ProtocolError):
                decoder.feed(b'x')
        for raw in [b'\x00', struct.pack('!I', 2), struct.pack('!I', 2) + b'x']:
            decoder = FrameDecoder()
            decoder.feed(raw)
            with self.assertRaises(ProtocolError):
                decoder.finish()

    def test_partial_writes_backpressure(self):
        output = bytearray()
        pending = SendBuffer(budget=12)
        pending.enqueue(b'ab')
        pending.enqueue(b'cd')
        with self.assertRaises(BufferError):
            pending.enqueue(b'e')
        self.assertEqual(pending.queued, 12)
        def blocked(data):
            raise BlockingIOError()
        pending.flush_once(blocked)
        self.assertEqual(pending.queued, 12)
        def partial(data):
            output.extend(data[:2])
            return min(2, len(data))
        while pending.queued:
            pending.flush_once(partial)
        self.assertEqual(bytes(output), encode_frame(b'ab') + encode_frame(b'cd'))
        pending.enqueue(b'z')
        with self.assertRaises(EOFError):
            pending.flush_once(lambda data: 0)
        self.assertEqual(pending.queued, 5)


class HeartbeatTests(unittest.TestCase):
    def test_poll_frequency_independent(self):
        for times in [[106], [101, 102, 103, 104, 105, 106]]:
            hb = HeartbeatManager(start=100)
            expired = [hb.check_timeout(now) for now in times]
            self.assertTrue(expired[-1])
            self.assertFalse(hb.connected)
            self.assertFalse(hb.check_timeout(107))

    def test_session_ack_and_expiry(self):
        hb = HeartbeatManager(generation='new', start=0)
        token = hb.send_heartbeat(2)
        self.assertFalse(hb.receive_heartbeat(('old', 1), 2))
        self.assertEqual(hb.send_heartbeat(4), token)
        self.assertTrue(hb.receive_heartbeat(token, 5))
        self.assertFalse(hb.receive_heartbeat(token, 5))
        next_token = hb.send_heartbeat(6)
        self.assertNotEqual(token, next_token)
        self.assertFalse(hb.receive_heartbeat(next_token, 11))
        self.assertFalse(hb.connected)
        with self.assertRaises(ValueError):
            hb.check_timeout(10)


class ReconciliationTests(unittest.TestCase):
    def test_original_dt_prefix_and_monotonic_sequence(self):
        sync = StateSyncDemo()
        commands = [sync.client_tick(dt, dx, dy) for dt, dx, dy in [(0.1, 1, 0), (0.2, 0, 1), (0.05, 0, 0)]]
        predicted = sync.client_position
        for command in commands:
            self.assertTrue(sync.server_receive_input(command))
            self.assertFalse(sync.server_receive_input(command))
            self.assertTrue(sync.reconcile(sync.server_snapshot()))
            self.assertEqual(sync.client_position, predicted)
        self.assertEqual(sync.server_position, predicted)
        self.assertFalse(sync.pending_inputs)
        self.assertEqual(sync.client_tick(0.1, -1, 0).seq, 4)

    def test_stale_future_and_gap(self):
        sync = StateSyncDemo()
        command = sync.client_tick(0.1, 1, 0)
        sync.server_receive_input(command)
        snapshot = sync.server_snapshot()
        sync.reconcile(snapshot)
        self.assertFalse(sync.reconcile(snapshot))
        self.assertFalse(sync.reconcile(Snapshot(2, 0, 0, 0)))
        before = (sync.client_position, sync.last_snapshot, sync.next_input)
        for bad in [Snapshot(2, 2, 0, 0), Snapshot(2, 1, float('nan'), 0), Snapshot(True, 1, 0, 0)]:
            with self.assertRaises(ProtocolError):
                sync.reconcile(bad)
            self.assertEqual((sync.client_position, sync.last_snapshot, sync.next_input), before)
        with self.assertRaises(ResyncRequired):
            sync.server_receive_input(Input(3, 0.1, 1, 0))
        self.assertEqual(sync.server_ack, 1)

    def test_authority_correction_replays_only_unconfirmed_suffix(self):
        sync = StateSyncDemo()
        sync.client_tick(0.1, 1, 0)
        second = sync.client_tick(0.2, 1, 0)
        sync.reconcile(Snapshot(1, 1, 10.0, 2.0))
        self.assertEqual(sync.client_position, (10.2, 2.0))
        self.assertEqual(list(sync.pending_inputs), [second])
        self.assertEqual(sync.next_input, 3)
        sync.reconcile(Snapshot(2, 2, 10.2, 2.0))
        self.assertFalse(sync.pending_inputs)
        self.assertEqual(sync.client_position, (10.2, 2.0))

    def test_pending_exhaustion_and_bad_input_preserve_state(self):
        sync = StateSyncDemo(pending_limit=1)
        with self.assertRaises(ProtocolError):
            sync.client_tick(1, 1, 0)
        self.assertEqual(sync.next_input, 1)
        command = sync.client_tick(0.1, 1, 0)
        with self.assertRaises(ResyncRequired):
            sync.client_tick(0.1, 1, 0)
        self.assertEqual(list(sync.pending_inputs), [command])
        self.assertEqual(sync.next_input, 2)


if __name__ == '__main__':
    unittest.main()
