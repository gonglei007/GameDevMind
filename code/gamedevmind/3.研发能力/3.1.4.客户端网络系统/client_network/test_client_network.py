import threading
import unittest
from client_network import ClientNetwork, Event, State


class MaxJitter:
    def uniform(self, low, high):
        return high


def ready(client, now=0):
    generation = client.start(now)
    for kind in ('connected', 'auth_ok', 'restore_ok'):
        client.post(Event(generation, kind))
        client.pump(now)
    return generation


class LifecycleTests(unittest.TestCase):
    def test_requires_authentication_and_restore(self):
        client = ClientNetwork()
        generation = client.start(0)
        for expected, event in [(State.AUTHENTICATING, 'connected'), (State.RESTORING, 'auth_ok')]:
            client.post(Event(generation, event))
            client.pump(1)
            self.assertEqual(client.state, expected)
            with self.assertRaises(RuntimeError):
                client.begin_request(1, 2)
        client.post(Event(generation, 'restore_ok'))
        client.pump(2)
        self.assertEqual(client.state, State.READY)

    def test_old_connection_events_cannot_revive_or_complete(self):
        client = ClientNetwork(rng=MaxJitter())
        old = ready(client)
        request = client.begin_request(0, 10, 'order-1')
        client.post(Event(old, 'disconnected'))
        client.pump(1)
        self.assertEqual(client.state, State.BACKOFF)
        client.post(Event(old, 'connected'))
        client.post(Event(old, 'response', request.request_id))
        client.pump(1)
        self.assertEqual(client.state, State.BACKOFF)
        client.tick(client.retry_at)
        new = client.generation
        self.assertNotEqual(old, new)
        for kind in ('connected', 'auth_ok', 'restore_ok'):
            client.post(Event(new, kind))
        client.pump(client.last_now)
        self.assertEqual(client.state, State.READY)
        self.assertFalse(client.pending)  # no implicit request replay
        current = client.begin_request(client.last_now, 10, 'new-order')
        client.post(Event(old, 'response', current.request_id, b'wrong-generation'))
        client.pump(client.last_now)
        self.assertIn(current.request_id, client.pending)
        results = client.drain_results()
        self.assertEqual([(r.request_id, r.outcome, r.operation_key) for r in results],
                         [(request.request_id, 'unknown', 'order-1')])

    def test_out_of_order_responses_keep_request_identity(self):
        client = ClientNetwork()
        generation = ready(client)
        first = client.begin_request(0, 5, 'first')
        second = client.begin_request(0, 5, 'second')
        client.post(Event(generation, 'response', second.request_id, b'B'))
        client.post(Event(generation, 'response', first.request_id, b'A'))
        client.pump(1)
        self.assertEqual([(r.operation_key, r.body) for r in client.drain_results()],
                         [('second', b'B'), ('first', b'A')])

    def test_stage_and_total_deadlines(self):
        client = ClientNetwork(stage_timeout=2, recovery_timeout=5, rng=MaxJitter())
        old = client.start(0)
        client.post(Event(old, 'connected'))
        client.pump(2)  # event at deadline loses to timeout, even if already queued
        self.assertEqual(client.state, State.BACKOFF)
        client.tick(client.retry_at)
        generation = client.generation
        client.post(Event(generation, 'connected'))
        client.pump(4)
        client.post(Event(generation, 'auth_ok'))
        client.pump(4.5)
        client.post(Event(generation, 'restore_ok'))
        client.pump(5)
        self.assertEqual(client.state, State.FAILED)
        self.assertEqual(client.reason, 'recovery_timeout')

    def test_max_attempts_and_full_jitter_bound(self):
        client = ClientNetwork(max_attempts=2, rng=MaxJitter())
        generation = client.start(0)
        client.post(Event(generation, 'disconnected'))
        client.pump(0)
        self.assertEqual(client.retry_at, 1)
        client.tick(1)
        client.post(Event(client.generation, 'disconnected'))
        client.pump(1)
        self.assertEqual(client.state, State.FAILED)
        client.tick(100)
        self.assertEqual(client.attempts, 2)

    def test_permanent_rejections_do_not_retry(self):
        for reason in ('auth_failed', 'update_required'):
            client = ClientNetwork()
            generation = client.start(0)
            client.post(Event(generation, 'connected'))
            client.post(Event(generation, reason))
            client.pump(0)
            client.tick(100)
            self.assertEqual(client.state, State.BLOCKED)
            self.assertEqual(client.reason, reason)
            self.assertEqual(client.attempts, 1)
            with self.assertRaises(RuntimeError):
                client.start(100)

    def test_completion_once_for_cancel_timeout_duplicate_and_out_of_order(self):
        client = ClientNetwork()
        generation = ready(client)
        first = client.begin_request(0, 2, 'first')
        second = client.begin_request(0, 2, 'second')
        third = client.begin_request(0, 2, 'third')
        self.assertTrue(client.cancel(first.request_id, 1))
        client.post(Event(generation, 'response', second.request_id, b'ok'))
        client.post(Event(generation, 'response', second.request_id, b'duplicate'))
        client.post(Event(generation, 'response', first.request_id, b'late'))
        client.pump(1)
        client.post(Event(generation, 'response', third.request_id, b'at-deadline'))
        client.pump(2)
        results = client.drain_results()
        self.assertEqual([(r.operation_key, r.outcome, r.reason) for r in results],
                         [('first', 'unknown', 'cancelled'), ('second', 'response', 'response'),
                          ('third', 'unknown', 'timeout')])
        self.assertFalse(client.cancel(first.request_id, 2))
        self.assertFalse(client.drain_results())
        self.assertEqual(client.begin_request(2, 1).request_id, 4)

    def test_reserved_completion_capacity_and_close(self):
        client = ClientNetwork(capacity=2)
        ready(client)
        first = client.begin_request(0, 1)
        client.begin_request(0, 1)
        with self.assertRaises(BufferError):
            client.begin_request(0, 1)
        client.cancel(first.request_id, 0)
        with self.assertRaises(BufferError):
            client.begin_request(0, 1)  # undrained result still owns capacity
        client.close(0)
        client.close(0)
        client.tick(100)
        self.assertEqual(client.state, State.CLOSED)
        self.assertEqual(len(client.drain_results()), 2)
        with self.assertRaises(RuntimeError):
            client.begin_request(100, 1)

    def test_bounded_worker_mailbox_and_owner_dispatch(self):
        client = ClientNetwork(mailbox_capacity=2)
        generation = client.start(0)
        errors = []
        def worker():
            client.post(Event(generation, 'connected'))
            client.post(Event(generation, 'auth_ok'))
            for action in (lambda: client.post(Event(generation, 'restore_ok')), lambda: client.pump(0)):
                try:
                    action()
                except Exception as error:
                    errors.append(type(error))
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [BufferError, RuntimeError])
        self.assertEqual(client.state, State.CONNECTING)
        self.assertEqual(client.pump(0, limit=1), 1)
        self.assertEqual(client.state, State.AUTHENTICATING)
        client.pump(0)
        self.assertEqual(client.state, State.RESTORING)

    def test_invalid_time_event_and_configuration(self):
        for settings in ({'capacity': 0}, {'mailbox_capacity': 0}, {'stage_timeout': 0},
                         {'max_attempts': 0}, {'recovery_timeout': float('inf')}):
            with self.assertRaises(ValueError):
                ClientNetwork(**settings)
        client = ClientNetwork()
        client.start(1)
        for now in (0, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                client.tick(now)
        for event in (Event(1, 'unknown'), Event(1, 'response', body=b'x' * 4097), Event(0, 'connected')):
            with self.assertRaises(ValueError):
                client.post(event)


if __name__ == '__main__':
    unittest.main()
