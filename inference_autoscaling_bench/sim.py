"""A discrete-event model of an LLM inference deployment behind an autoscaler.

What is modelled, and where it is a simplification (docs/methodology.md says why each is acceptable):

* A pod serves up to `slots` requests at once, the way a vLLM server batches. A request's prefill and per-token decode
  times grow with how many requests share the pod when it starts (continuous batching slows everyone a little).
* Requests wait in one queue and start on the least-loaded ready pod with a free slot. One queue stands in for a
  perfect router, so the benchmark isolates autoscaling from routing (the sibling routing benchmark covers routing).
* A new pod is not ready until `startup_s` has passed (scheduling, image, model load), and costs from creation.
* Scaling down removes pods still starting first, then the ready pods holding the fewest requests. A removed pod
  takes no new requests, finishes the ones it has, and stops costing when it is empty. Nothing is dropped.
* The autoscaler runs every `SYNC_PERIOD_S` seconds, the HPA default, and sees only what a metrics pipeline would.
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass

from .policies import Bounds, Observation, Policy
from .workload import Request, Workload

SYNC_PERIOD_S = 15.0
RATE_WINDOW_S = 30.0

_DONE, _READY, _ARRIVAL, _TICK = 0, 1, 2, 3  # the order events at the same instant are handled in


@dataclass(frozen=True)
class Replica:
    slots: int = 8
    prefill_tokens_per_s: float = 4000.0
    seconds_per_output_token: float = 0.020
    prefill_slowdown: float = 0.5   # extra prefill time at a full pod, as a fraction of the unloaded time
    decode_slowdown: float = 0.6    # the same for each output token
    startup_s: float = 45.0

    def __post_init__(self):
        if self.slots < 1 or self.startup_s < 0:
            raise ValueError("a replica needs at least one slot and a non-negative startup time")


class _Pod:
    __slots__ = ("id", "born", "ready_at", "state", "running", "died")

    def __init__(self, ident: int, born: float, ready_at: float, state: str):
        self.id, self.born, self.ready_at, self.state = ident, born, ready_at, state
        self.running = 0
        self.died: float | None = None


@dataclass
class Run:
    policy: str
    workload: str
    duration_s: float
    arrival: list[float]
    wait: list[float]            # seconds from arrival to the start of service
    ttft: list[float]            # seconds to the first token
    latency: list[float]         # seconds to the last token
    timeline: list[tuple[float, int, int, int, int]]   # (second, ready, pending, running, queued) at every sync
    events: list[tuple[float, int]]                    # (second, change in replicas) for every scaling decision
    replica_seconds: float
    peak_replicas: int
    max_queue: int


def simulate(trace: list[Request], workload: Workload, policy: Policy, replica: Replica = Replica(),
             bounds: Bounds = Bounds()) -> Run:
    n = len(trace)
    duration = workload.duration_s
    wait, ttft, latency = [0.0] * n, [0.0] * n, [0.0] * n
    pods: list[_Pod] = []
    queue: deque[int] = deque()
    heap: list[tuple[float, int, int, object]] = []
    counter = 0
    state = {"running": 0, "live": 0, "peak": 0, "max_queue": 0}
    arrivals: deque[float] = deque()
    timeline: list[tuple[float, int, int, int, int]] = []
    events: list[tuple[float, int]] = []

    def push(t: float, kind: int, payload: object) -> None:
        nonlocal counter
        heapq.heappush(heap, (t, kind, counter, payload))
        counter += 1

    def add_pod(now: float, ready_at: float, pod_state: str) -> None:
        pod = _Pod(len(pods), now, ready_at, pod_state)
        pods.append(pod)
        state["live"] += 1
        state["peak"] = max(state["peak"], state["live"])
        if pod_state == "pending":
            push(ready_at, _READY, pod)

    def retire(pod: _Pod, now: float) -> None:
        pod.state, pod.died = "gone", now
        state["live"] -= 1

    def dispatch(now: float) -> None:
        while queue:
            best = None
            for pod in pods:
                if pod.state == "ready" and pod.running < replica.slots and (best is None or pod.running < best.running):
                    best = pod
            if best is None:
                return
            i = queue.popleft()
            req = trace[i]
            best.running += 1
            state["running"] += 1
            share = (best.running - 1) / replica.slots
            prefill = req.prompt_tokens / replica.prefill_tokens_per_s * (1 + replica.prefill_slowdown * share)
            step = replica.seconds_per_output_token * (1 + replica.decode_slowdown * share)
            wait[i] = now - req.arrival
            ttft[i] = wait[i] + prefill + step
            latency[i] = wait[i] + prefill + req.output_tokens * step
            push(now + prefill + req.output_tokens * step, _DONE, (best, i))

    for _ in range(policy.initial(bounds)):
        add_pod(0.0, 0.0, "ready")
    for req in trace:
        push(req.arrival, _ARRIVAL, req.index)
    tick = SYNC_PERIOD_S
    while tick <= duration:
        push(tick, _TICK, None)
        tick += SYNC_PERIOD_S
    push(0.0, _TICK, None)

    while heap:
        now, kind, _, payload = heapq.heappop(heap)
        if kind == _DONE:
            pod, _i = payload
            pod.running -= 1
            state["running"] -= 1
            if pod.state == "draining" and pod.running == 0:
                retire(pod, now)
            dispatch(now)
        elif kind == _READY:
            if payload.state == "pending":
                payload.state = "ready"
                dispatch(now)
        elif kind == _ARRIVAL:
            queue.append(payload)
            arrivals.append(now)
            state["max_queue"] = max(state["max_queue"], len(queue))
            dispatch(now)
        else:
            ready = [p for p in pods if p.state == "ready"]
            pending = [p for p in pods if p.state == "pending"]
            timeline.append((now, len(ready), len(pending), state["running"], len(queue)))
            while arrivals and arrivals[0] <= now - RATE_WINDOW_S:
                arrivals.popleft()
            window = min(now, RATE_WINDOW_S)
            obs = Observation(now, len(ready), len(pending), state["running"], len(queue), replica.slots,
                              len(arrivals) / window if window > 0 else 0.0)
            desired = policy.decide(obs, bounds)
            if desired is None or now == 0.0:
                continue
            current = len(ready) + len(pending)
            if desired > current:
                for _ in range(desired - current):
                    add_pod(now, now + replica.startup_s, "pending")
            elif desired < current:
                for pod in sorted(pending, key=lambda p: -p.id)[:current - desired]:
                    retire(pod, now)
                removed = current - desired - min(len(pending), current - desired)
                for pod in sorted(ready, key=lambda p: (p.running, -p.id))[:removed]:
                    if pod.running == 0:
                        retire(pod, now)
                    else:
                        pod.state = "draining"
            if desired != current:
                events.append((now, desired - current))
            dispatch(now)

    if queue:
        raise RuntimeError(f"{len(queue)} requests never started: no pod was ready and none was on the way")
    cost = sum(max(0.0, min(p.died if p.died is not None else duration, duration) - min(p.born, duration)) for p in pods)
    return Run(policy.name, workload.name, duration, [r.arrival for r in trace], wait, ttft, latency, timeline, events,
               cost, state["peak"], state["max_queue"])
