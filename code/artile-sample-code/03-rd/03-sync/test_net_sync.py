import unittest
from net_sync import (NetworkSimulator, InterpolationBuffer, EntitySnapshot, Client, Server,
                      ProtocolError, ResyncRequired, simulate)


class DelayedChannelTests(unittest.TestCase):
    def test_delivery_uses_injected_time_and_can_reorder(self):
        channel = NetworkSimulator()
        channel.send('slow', 0, delay=0.2)
        channel.send('fast', 0, delay=0.1)
        self.assertEqual(channel.receive(0.099), [])
        self.assertEqual(channel.receive(0.1), ['fast'])
        self.assertEqual(channel.receive(0.2), ['slow'])
        self.assertFalse(channel.queue)
        with self.assertRaises(ValueError):
            channel.receive(0.1)

    def test_channel_budget_is_explicit(self):
        channel = NetworkSimulator(capacity=1)
        channel.send('first', 0)
        with self.assertRaises(BufferError):
            channel.send('second', 0)
        self.assertEqual(channel.receive(1), ['first'])
        client = Client(NetworkSimulator(capacity=1), NetworkSimulator(), NetworkSimulator())
        command = client.apply_input(0.1, 1, 0, 0)
        with self.assertRaises(ResyncRequired):
            client.apply_input(0.1, 1, 0, 0)
        self.assertEqual(list(client.model.pending_inputs), [command])

    def test_persistent_two_player_simulation_drains_and_converges(self):
        clients, server, now = simulate()
        self.assertGreater(now, 0.2)
        self.assertEqual(len(clients), 2)
        self.assertAlmostEqual(server.models[0].server_position[0], 0)
        self.assertAlmostEqual(server.models[1].server_position[1], 0.45)
        for index, client in enumerate(clients):
            self.assertFalse(client.model.pending_inputs)
            self.assertEqual(client.model.last_ack, 31)
            self.assertEqual(client.model.client_position, server.models[index].server_position)
            self.assertTrue(client.interpolation.samples)

    def test_two_one_way_delays_are_not_100ms_rtt(self):
        inputs = [NetworkSimulator() for _ in range(2)]
        outputs = [NetworkSimulator() for _ in range(2)]
        remotes = [NetworkSimulator() for _ in range(2)]
        client = Client(inputs[0], outputs[0], remotes[0])
        server = Server(inputs, outputs, remotes)
        client.apply_input(0.1, 1, 0, 0)
        server.tick(0.1)
        client.update(0.199)
        self.assertEqual(client.model.last_ack, 0)
        client.update(0.2)
        self.assertEqual(client.model.last_ack, 1)
        self.assertFalse(client.model.pending_inputs)


class InterpolationTests(unittest.TestCase):
    def test_rolling_brackets_bounded_history_and_no_extrapolation(self):
        buffer = InterpolationBuffer(capacity=3)
        self.assertIsNone(buffer.sample(0))
        for seq in range(1, 5):
            self.assertTrue(buffer.add(EntitySnapshot(seq, seq, seq * 10, 0)))
        self.assertEqual([s.sequence for s in buffer.samples], [2, 3, 4])
        self.assertEqual(buffer.sample(2.5), (25, 0))
        self.assertEqual(buffer.sample(3.5), (35, 0))
        self.assertEqual(buffer.sample(1), (20, 0))
        self.assertEqual(buffer.sample(10), (40, 0))
        for stale in [EntitySnapshot(3, 5, 100, 0), EntitySnapshot(5, 4, 100, 0)]:
            self.assertFalse(buffer.add(stale))
        with self.assertRaises(ProtocolError):
            buffer.add(EntitySnapshot(5, 5, float('nan'), 0))
        with self.assertRaises(ValueError):
            buffer.sample(float('inf'))
        self.assertEqual(buffer.sample(10), (40, 0))


if __name__ == '__main__':
    unittest.main()
