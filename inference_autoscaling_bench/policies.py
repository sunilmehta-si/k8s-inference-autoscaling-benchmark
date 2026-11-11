"""Autoscaling policies: what a policy sees every sync period, and the replica count it asks for.

`Hpa` follows the Kubernetes HorizontalPodAutoscaler's algorithm for a per-pod metric, step by step, because the
differences between signals are only meaningful if the controller around them is the real one:

  1. ratio = average metric over the ready pods / target. Within `tolerance` (0.1) of 1, change nothing.
  2. When the ratio is above 1 and some pods are not ready yet, recompute it as if each of those pods used none of
     the metric (the controller does this so that pods still starting are not ignored). If that moves the ratio
     inside the tolerance, or across 1, change nothing; otherwise it sets the count.
  3. desired = ceil(ratio * pods counted), bounded by the minimum and maximum.
  4. Stabilization: scaling up follows the lowest recommendation in the up window (0 s by default, so the latest);
     scaling down follows the highest recommendation in the down window (300 s by default).
  5. Scale-up rate limit: at most the larger of +4 pods and doubling per sync period (the default policies).

With `external=True` it follows the same controller reading the signal as KEDA serves it: an external metric, the sum
over the pods, with a target per pod. The controller averages that over every pod the Deployment has, ready or still
starting, and within the tolerance changes nothing; otherwise it asks for ceil(sum / target). Step 2 does not apply, so
pods still starting count in the average whatever the direction, and no ready pod is needed for a decision. Steps 4 and
5 are the same.

`Predictive` is the same controller with a forecast beside it: at every sync it feeds the arrival rate to a forecaster
(`forecast.Holt`) and asks for the pods the rate forecast `horizon_s` seconds ahead needs, by default one pod startup
ahead, so pods ordered now are ready when the load arrives. On the rate signal the forecast is the metric; on the
others the metric is scaled by how much the rate is forecast to grow (by Little's law, requests in the system, and
the busy slots and the queue that hold them, grow with the arrival rate while the time a request spends there holds).
It moves to the larger of that and the HPA's own recommendation, then through the same bounds, windows and limit.
With `floor=False` the forecast alone decides whenever there is one, so a forecast fall can ask for fewer pods than the
HPA would (the scale-down window still holds them for its 300 s).

Request concurrency, queue depth, slot utilization and request rate are the four signals compared. They are
inputs to the same controller, so a difference between them is a difference in the signal.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from .forecast import Holt


@dataclass(frozen=True)
class Bounds:
    min_replicas: int = 2
    max_replicas: int = 32


@dataclass(frozen=True)
class Observation:
    now: float
    ready: int          # pods serving traffic
    pending: int        # pods created and still starting
    running: int        # requests being served, over all pods
    queued: int         # requests waiting for a free slot
    slots: int          # concurrent requests one pod can serve
    arrival_rate: float  # requests per second over the trailing rate window


class Policy:
    name = "policy"

    def initial(self, bounds: Bounds) -> int:
        return bounds.min_replicas

    def decide(self, obs: Observation, bounds: Bounds) -> int | None:
        """The replica count to move to, or None to leave it."""
        return None


class Static(Policy):
    def __init__(self, replicas: int):
        self.replicas = replicas
        self.name = f"static-{replicas}"

    def initial(self, bounds: Bounds) -> int:
        return self.replicas


# signal name -> (metric summed over the ready pods, default target per pod)
SIGNALS = {
    "utilization": (lambda o: o.running / o.slots, 0.6),       # busy slots over slots, what GPU utilization stands in for
    "concurrency": (lambda o: o.running + o.queued, 6.0),      # requests in the system per pod
    "queue": (lambda o: float(o.queued), 1.0),                 # requests waiting per pod
    "rps": (lambda o: o.arrival_rate, 1.4),                    # requests per second per pod
}


class Hpa(Policy):
    def __init__(self, signal: str, target: float | None = None, down_window_s: float = 300.0, up_window_s: float = 0.0,
                 tolerance: float = 0.1, up_pods: int = 4, up_percent: float = 100.0, name: str | None = None,
                 external: bool = False):
        if signal not in SIGNALS:
            raise ValueError(f"unknown signal {signal!r}; choose from {', '.join(SIGNALS)}")
        self.signal = signal
        self.metric, default_target = SIGNALS[signal]
        self.target = default_target if target is None else target
        if self.target <= 0:
            raise ValueError("the target must be positive")
        self.down_window_s, self.up_window_s = down_window_s, up_window_s
        self.tolerance, self.up_pods, self.up_percent = tolerance, up_pods, up_percent
        self.external = external
        self.name = name or f"{'keda' if external else 'hpa'}-{signal}"
        self.history: deque[tuple[float, int]] = deque()

    def decide(self, obs: Observation, bounds: Bounds) -> int | None:
        desired = self.recommend(obs)
        if desired is None:
            return None
        return self._remember(obs.now, desired, obs.ready + obs.pending, bounds)

    def recommend(self, obs: Observation) -> int | None:
        """Steps 1 to 3 before the bounds: the replica count this sync's metric asks for (the current count when it
        changes nothing), or None when there is no metric to act on."""
        current = obs.ready + obs.pending
        if self.external:
            if current == 0:
                return None
            total = self.metric(obs)
            ratio = total / current / self.target
            return current if abs(ratio - 1) <= self.tolerance else math.ceil(total / self.target)
        if obs.ready == 0:
            return None  # no metric from any pod: the controller leaves the count alone
        total = self.metric(obs)
        ratio = total / obs.ready / self.target
        if abs(ratio - 1) <= self.tolerance:
            return current
        counted = obs.ready
        if ratio > 1 and obs.pending > 0:
            counted = obs.ready + obs.pending
            new_ratio = total / counted / self.target
            if abs(new_ratio - 1) <= self.tolerance or (new_ratio < 1 < ratio):
                return current
            ratio = new_ratio
        return math.ceil(ratio * counted)

    def _remember(self, now: float, desired: int, current: int, bounds: Bounds) -> int:
        desired = max(bounds.min_replicas, min(bounds.max_replicas, desired))
        self.history.append((now, desired))
        horizon = max(self.up_window_s, self.down_window_s)
        while self.history and now - self.history[0][0] > horizon:
            self.history.popleft()
        up, down = desired, desired
        for t, rec in self.history:
            if now - t <= self.up_window_s:
                up = min(up, rec)
            if now - t <= self.down_window_s:
                down = max(down, rec)
        result = current
        if result < up:
            result = up
        if result > down:
            result = down
        if result > current:
            result = min(result, max(current + self.up_pods, math.ceil(current * (1 + self.up_percent / 100))))
        return max(bounds.min_replicas, min(bounds.max_replicas, result))


class Predictive(Hpa):
    def __init__(self, signal: str, horizon_s: float = 45.0, alpha: float = 0.5, beta: float = 0.3,
                 floor: bool = True, name: str | None = None, **hpa):
        if horizon_s < 0:
            raise ValueError("the horizon cannot be negative")
        super().__init__(signal, name=name or f"predict-{signal}", **hpa)
        self.horizon_s = horizon_s
        self.forecaster = Holt(alpha, beta)
        self.floor = floor   # never ask for fewer pods than the HPA would

    def decide(self, obs: Observation, bounds: Bounds) -> int | None:
        self.forecaster.update(obs.now, obs.arrival_rate)
        reactive = self.recommend(obs)
        if reactive is None:
            return None
        current = obs.ready + obs.pending
        predicted = self.predict(obs)
        if predicted is None:
            desired = reactive
        else:
            desired = max(reactive, predicted) if self.floor else predicted
        return self._remember(obs.now, desired, current, bounds)

    def predict(self, obs: Observation) -> int | None:
        """The pods the metric forecast `horizon_s` ahead needs at the target (the current count when that is within the
        tolerance), or None when nothing is arriving, so there is no growth to scale by."""
        if obs.arrival_rate <= 0:
            return None
        growth = self.forecaster.forecast(self.horizon_s) / obs.arrival_rate
        needed = self.metric(obs) * growth / self.target
        current = obs.ready + obs.pending
        if current and abs(needed / current - 1) <= self.tolerance:
            return current
        return math.ceil(needed)
