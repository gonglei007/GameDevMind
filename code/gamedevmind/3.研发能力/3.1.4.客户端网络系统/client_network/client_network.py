"""Single-owner lifecycle model, bounded worker mailbox, no actual transport or Unity API."""
from collections import deque
from dataclasses import dataclass
from enum import Enum
import math
import queue
import random
import threading


class State(Enum):
    IDLE = 'idle'
    CONNECTING = 'connecting'
    AUTHENTICATING = 'authenticating'
    RESTORING = 'restoring'
    READY = 'ready'
    BACKOFF = 'backoff'
    FAILED = 'failed'
    BLOCKED = 'blocked'
    CLOSED = 'closed'


@dataclass(frozen=True)
class Event:
    generation: int
    kind: str
    request_id: int = 0
    body: bytes = b''


@dataclass(frozen=True)
class Request:
    request_id: int
    generation: int
    deadline: float
    operation_key: str


@dataclass(frozen=True)
class Result:
    request_id: int
    outcome: str
    reason: str
    operation_key: str
    body: bytes = b''


class ClientNetwork:
    """Owner thread calls every method except post(). Adapt transport events through pump().

    Requests are assumed handed to transport immediately: cancel/timeout/disconnect mean
    UNKNOWN business outcome, never 'definitely not committed'. No automatic request replay.
    """
    def __init__(self, capacity=16, mailbox_capacity=32, stage_timeout=5.0,
                 recovery_timeout=30.0, max_attempts=4, rng=None):
        if (type(capacity) is not int or capacity < 1 or type(mailbox_capacity) is not int or
                mailbox_capacity < 1 or type(max_attempts) is not int or max_attempts < 1 or
                not 0 < stage_timeout <= recovery_timeout or not math.isfinite(recovery_timeout)):
            raise ValueError('invalid budget')
        self.owner = threading.get_ident()
        self.capacity, self.stage_timeout = capacity, stage_timeout
        self.recovery_timeout, self.max_attempts = recovery_timeout, max_attempts
        self.rng = rng or random.Random()
        self.mailbox = queue.Queue(maxsize=mailbox_capacity)
        self.state, self.generation, self.attempts = State.IDLE, 0, 0
        self.last_now = -math.inf
        self.stage_deadline = self.recovery_deadline = self.retry_at = None
        self.next_request = 1
        self.pending, self.results = {}, deque()
        self.reason = ''

    def _owner(self):
        if threading.get_ident() != self.owner:
            raise RuntimeError('lifecycle and UI-facing results belong to owner thread')

    def _time(self, now):
        self._owner()
        if not math.isfinite(now) or now < self.last_now:
            raise ValueError('use a monotonic clock')
        self.last_now = now

    def post(self, event):
        """Worker ingress. Full mailbox is an explicit adapter failure, never silent loss."""
        if (type(event) is not Event or type(event.generation) is not int or event.generation < 1 or
                event.kind not in {'connected', 'auth_ok', 'auth_failed', 'restore_ok',
                                   'update_required', 'disconnected', 'response'} or
                type(event.request_id) is not int or event.request_id < 0 or
                type(event.body) is not bytes or len(event.body) > 4096):
            raise ValueError('invalid transport event')
        try:
            self.mailbox.put_nowait(event)
        except queue.Full as error:
            raise BufferError('mailbox full: adapter must stop admission and report failure') from error

    def _complete(self, request_id, outcome, reason, body=b''):
        request = self.pending.pop(request_id)
        self.results.append(Result(request_id, outcome, reason, request.operation_key, body))

    def _invalidate(self, reason):
        self.generation += 1
        for request_id in list(self.pending):
            self._complete(request_id, 'unknown', reason)
        self.stage_deadline = None

    def _attempt(self, now):
        self.generation += 1
        self.attempts += 1
        self.state = State.CONNECTING
        self.stage_deadline = min(now + self.stage_timeout, self.recovery_deadline)
        self.retry_at = None

    def start(self, now):
        self._time(now)
        if self.state not in {State.IDLE, State.FAILED}:
            raise RuntimeError('cannot start in current state')
        self.attempts, self.reason = 0, ''
        self.recovery_deadline = now + self.recovery_timeout
        self._attempt(now)
        return self.generation

    def _failed(self, now, reason):
        was_ready = self.state == State.READY
        self._invalidate(reason)
        self.reason = reason
        if was_ready:
            self.attempts = 0
            self.recovery_deadline = now + self.recovery_timeout
        if now >= self.recovery_deadline or self.attempts >= self.max_attempts:
            self.state, self.retry_at = State.FAILED, None
            return
        ceiling = min(8.0, 0.5 * (2 ** min(self.attempts, 5)))
        self.retry_at = now + self.rng.uniform(0, ceiling)
        self.state = State.BACKOFF

    def tick(self, now):
        self._time(now)
        for request_id, request in list(self.pending.items()):
            if now >= request.deadline:
                self._complete(request_id, 'unknown', 'timeout')
        active = {State.CONNECTING, State.AUTHENTICATING, State.RESTORING, State.BACKOFF}
        if self.state in active and now >= self.recovery_deadline:
            self._invalidate('recovery_timeout')
            self.state, self.reason, self.retry_at = State.FAILED, 'recovery_timeout', None
        elif self.state == State.BACKOFF and now >= self.retry_at:
            self._attempt(now)
        elif self.state in active and self.stage_deadline is not None and now >= self.stage_deadline:
            self._failed(now, 'stage_timeout')

    def pump(self, now, limit=8):
        self.tick(now)
        if type(limit) is not int or limit < 1:
            raise ValueError('invalid dispatch budget')
        handled = 0
        while handled < limit:
            try:
                event = self.mailbox.get_nowait()
            except queue.Empty:
                break
            handled += 1
            if event.generation != self.generation:
                continue
            if event.kind == 'connected' and self.state == State.CONNECTING:
                self.state = State.AUTHENTICATING
                self.stage_deadline = min(now + self.stage_timeout, self.recovery_deadline)
            elif event.kind == 'auth_ok' and self.state == State.AUTHENTICATING:
                self.state = State.RESTORING
                self.stage_deadline = min(now + self.stage_timeout, self.recovery_deadline)
            elif event.kind == 'restore_ok' and self.state == State.RESTORING:
                self.state, self.stage_deadline = State.READY, None
            elif event.kind in {'auth_failed', 'update_required'} and self.state in {
                    State.AUTHENTICATING, State.RESTORING, State.READY}:
                self._invalidate(event.kind)
                self.state, self.reason = State.BLOCKED, event.kind
            elif event.kind == 'disconnected' and self.state in {
                    State.CONNECTING, State.AUTHENTICATING, State.RESTORING, State.READY}:
                self._failed(now, 'disconnected')
            elif event.kind == 'response' and self.state == State.READY:
                request = self.pending.get(event.request_id)
                if request is not None and request.generation == event.generation:
                    self._complete(event.request_id, 'response', 'response', event.body)
        return handled

    def begin_request(self, now, timeout, operation_key=''):
        self.tick(now)
        if self.state != State.READY:
            raise RuntimeError('connection is not restored and ready')
        if not 0 < timeout or not math.isfinite(timeout):
            raise ValueError('invalid request timeout')
        if type(operation_key) is not str or len(operation_key.encode('utf-8')) > 128:
            raise ValueError('invalid operation key')
        # Reserve one result slot at admission, so terminal paths never overflow results.
        if len(self.pending) + len(self.results) >= self.capacity:
            raise BufferError('request/result budget exhausted')
        request = Request(self.next_request, self.generation, now + timeout, operation_key)
        self.next_request += 1
        self.pending[request.request_id] = request
        return request

    def cancel(self, request_id, now):
        self.tick(now)
        if request_id not in self.pending:
            return False
        self._complete(request_id, 'unknown', 'cancelled')
        return True

    def drain_results(self, limit=8):
        self._owner()
        if type(limit) is not int or limit < 1:
            raise ValueError('invalid result dispatch budget')
        return [self.results.popleft() for _ in range(min(limit, len(self.results)))]

    def close(self, now):
        self._time(now)
        if self.state != State.CLOSED:
            self._invalidate('closed')
            self.state, self.reason, self.retry_at = State.CLOSED, 'closed', None


def main():
    client = ClientNetwork(rng=random.Random(7))
    generation = client.start(0)
    for kind in ('connected', 'auth_ok', 'restore_ok'):
        client.post(Event(generation, kind))
        client.pump(0)
    request = client.begin_request(0, 2, 'order-demo-1')
    client.cancel(request.request_id, 1)
    client.post(Event(generation, 'response', request.request_id, b'late success'))
    client.pump(1)
    result, = client.drain_results()
    assert result.outcome == 'unknown' and result.operation_key == 'order-demo-1'
    client.close(1)
    print('PASS: ready requires auth+restore; cancel completes once with unknown outcome')
    print('Model only: no DNS/TLS/Socket, Unity integration or server-side idempotency')


if __name__ == '__main__':
    main()
