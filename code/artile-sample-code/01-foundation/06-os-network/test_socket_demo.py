import struct
import unittest
from socket_demo import LatestPosition, ProtocolError, encode_position, tcp_roundtrip, udp_roundtrip


class SocketTests(unittest.TestCase):
    def test_real_tcp_loopback(self):
        messages = ['玩家😀'.encode(), b'\x00\xff', b'x' * 16384]
        self.assertEqual(tcp_roundtrip(messages), messages)
        self.assertEqual(tcp_roundtrip([]), [])

    def test_real_udp_with_deterministic_faults(self):
        adopted, state = udp_roundtrip()
        self.assertEqual(adopted, [1, 2, 5, 7, 8])
        self.assertEqual(state.position, (8, 0, 0))

    def test_datagram_validation_preserves_state(self):
        state = LatestPosition()
        self.assertTrue(state.receive(encode_position(2, 1, 2, 3)))
        for raw in [b'', b'x' * 15, b'x' * 17, struct.pack('!Ifff', 0, 0, 0, 0),
                    struct.pack('!Ifff', 3, float('nan'), 0, 0)]:
            with self.assertRaises(ProtocolError):
                state.receive(raw)
            self.assertEqual(state.sequence, 2)
        self.assertFalse(state.receive(encode_position(1, 9, 9, 9)))
        self.assertFalse(state.receive(encode_position(2, 9, 9, 9)))
        self.assertEqual(state.position, (1, 2, 3))
        for seq in [0, -1, 1 << 32, True]:
            with self.assertRaises(ProtocolError):
                encode_position(seq, 0, 0, 0)


if __name__ == '__main__':
    unittest.main()
