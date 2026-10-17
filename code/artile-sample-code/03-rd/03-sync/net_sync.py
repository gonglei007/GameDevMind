#!/usr/bin/env python3
"""Deterministic delayed-channel model. No wall-clock sleeps, real sockets or engine physics."""
from dataclasses import dataclass
import heapq
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '02-technical' / '05-networking'))
from net_demo import StateSyncDemo, ProtocolError, ResyncRequired


class NetworkSimulator:
    """One direction only; delay is one-way, capacity is an explicit message budget."""
    def __init__(self, delay=0.1, capacity=128):
        if not math.isfinite(delay) or delay < 0 or type(capacity) is not int or capacity < 1:
            raise ValueError('invalid channel budget')
        self.delay, self.capacity = delay, capacity
        self.queue, self.serial, self.last_now = [], 0, -math.inf

    def _time(self, now):
        if not math.isfinite(now) or now < self.last_now:
            raise ValueError('use a monotonic simulation clock')
        self.last_now = now

    def send(self, message, now, delay=None):
        self._time(now)
        delay = self.delay if delay is None else delay
        if not math.isfinite(delay) or delay < 0:
            raise ValueError('invalid one-way delay')
        if len(self.queue) >= self.capacity:
            raise BufferError('channel budget exhausted; recovery required')
        self.serial += 1
        heapq.heappush(self.queue, (now + delay, self.serial, message))

    def receive(self, now):
        self._time(now)
        ready = []
        while self.queue and self.queue[0][0] <= now:
            ready.append(heapq.heappop(self.queue)[2])
        return ready


@dataclass(frozen=True)
class EntitySnapshot:
    sequence: int
    timestamp: float
    x: float
    y: float


class InterpolationBuffer:
    """Bounded remote-entity history in one server time domain; no clock sync or extrapolation."""
    def __init__(self, capacity=8):
        if type(capacity) is not int or capacity < 2:
            raise ValueError('need at least two samples')
        self.capacity, self.samples = capacity, []

    def add(self, snapshot):
        if (type(snapshot.sequence) is not int or snapshot.sequence < 1 or
                not all(math.isfinite(v) for v in (snapshot.timestamp, snapshot.x, snapshot.y))):
            raise ProtocolError('invalid entity snapshot')
        if self.samples and (snapshot.sequence <= self.samples[-1].sequence or
                             snapshot.timestamp <= self.samples[-1].timestamp):
            return False
        self.samples.append(snapshot)
        self.samples = self.samples[-self.capacity:]
        return True

    def sample(self, render_server_time):
        if not math.isfinite(render_server_time):
            raise ValueError('invalid render time')
        if not self.samples:
            return None
        if render_server_time <= self.samples[0].timestamp:
            first = self.samples[0]
            return first.x, first.y
        for previous, following in zip(self.samples, self.samples[1:]):
            if render_server_time <= following.timestamp:
                alpha = (render_server_time - previous.timestamp) / (following.timestamp - previous.timestamp)
                return (previous.x + (following.x - previous.x) * alpha,
                        previous.y + (following.y - previous.y) * alpha)
        latest = self.samples[-1]
        return latest.x, latest.y  # hold latest; caller must detect stale age


class Client:
    def __init__(self, outgoing, incoming, remote):
        self.outgoing, self.incoming, self.remote = outgoing, incoming, remote
        self.model, self.interpolation = StateSyncDemo(), InterpolationBuffer()

    def apply_input(self, dt, dx, dy, now):
        self.outgoing._time(now)
        if len(self.outgoing.queue) >= self.outgoing.capacity:
            raise ResyncRequired('channel full before prediction')
        command = self.model.client_tick(dt, dx, dy)
        self.outgoing.send(command, now)
        return command

    def update(self, now):
        for snapshot in self.incoming.receive(now):
            self.model.reconcile(snapshot)
        for snapshot in self.remote.receive(now):
            self.interpolation.add(snapshot)


class Server:
    def __init__(self, inputs, outputs, remote_outputs):
        if not len(inputs) == len(outputs) == len(remote_outputs) == 2:
            raise ValueError('this teaching server models exactly two players')
        self.inputs, self.outputs, self.remote_outputs = inputs, outputs, remote_outputs
        self.models = [StateSyncDemo() for _ in inputs]

    def tick(self, now):
        for index, incoming in enumerate(self.inputs):
            for command in incoming.receive(now):
                self.models[index].server_receive_input(command)
            snapshot = self.models[index].server_snapshot()
            self.outputs[index].send(snapshot, now)
            other = 1 - index
            self.remote_outputs[other].send(EntitySnapshot(snapshot.sequence, now, snapshot.x, snapshot.y), now)


def simulate():
    inputs = [NetworkSimulator() for _ in range(2)]
    outputs = [NetworkSimulator() for _ in range(2)]
    remotes = [NetworkSimulator() for _ in range(2)]
    clients = [Client(inputs[i], outputs[i], remotes[i]) for i in range(2)]
    server = Server(inputs, outputs, remotes)  # one persistent authoritative state
    now = 0.0
    for step in range(80):
        dt = (0.01, 0.02, 0.015)[step % 3]
        now += dt
        if step < 30:
            clients[0].apply_input(dt, 1 if step < 15 else -1, 0, now)
            clients[1].apply_input(dt, 0, 1, now)
        elif step == 30:
            for client in clients:
                client.apply_input(dt, 0, 0, now)  # explicit stop input
        server.tick(now)
        for client in clients:
            client.update(now)
    # Stop publishing and drain every in-flight input, authority and entity message.
    for step in range(40):
        now += 0.02
        if any(channel.queue for channel in inputs):
            server.tick(now)
        for client in clients:
            client.update(now)
    for index, client in enumerate(clients):
        assert not client.model.pending_inputs
        assert client.model.last_ack == server.models[index].server_ack == 31
        assert client.model.client_position == server.models[index].server_position
        assert client.interpolation.samples
    assert all(not channel.queue for channel in inputs + outputs + remotes)
    return clients, server, now


def main():
    clients, server, now = simulate()
    print('PASS: persistent authority, two independent directions, all 31 inputs acknowledged per player')
    print('Configured delay: 100ms each direction (nominal RTT 200ms, scheduling adds waiting)')
    print('PASS: stop + change direction + original dt replay; all channels drained')
    for index, client in enumerate(clients):
        print(f'player {index}: client={client.model.client_position}, server={server.models[index].server_position}')
    print('Local model only: no real network, clock synchronization, physics, AOI or performance claims')


if __name__ == '__main__':
    main()
