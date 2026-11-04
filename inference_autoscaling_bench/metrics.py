"""One run's numbers: what users felt (time to first token, goodput), what it cost (replica-seconds), and how the
autoscaler behaved (events, flapping, how long the service was unhealthy)."""
from __future__ import annotations

import math

from .sim import Run
from .workload import Workload

HEALTH_WINDOW_S = 10.0
FLAP_WINDOW_S = 120.0


def percentile(sorted_values: list[float], q: float) -> float:
    """Linear interpolation between the closest ranks, so the same inputs give the same answer everywhere."""
    if not sorted_values:
        raise ValueError("no values")
    position = (len(sorted_values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def summarize(run: Run, workload: Workload) -> dict:
    ttft = sorted(run.ttft)
    slo = workload.slo_ttft_s
    good = sum(1 for x in run.ttft if x <= slo)
    windows: dict[int, list[float]] = {}
    for arrival, value in zip(run.arrival, run.ttft):
        windows.setdefault(int(arrival // HEALTH_WINDOW_S), []).append(value)
    unhealthy = sum(HEALTH_WINDOW_S for values in windows.values() if percentile(sorted(values), 0.95) > slo)
    downs = [t for t, change in run.events if change < 0]
    ups = [t for t, change in run.events if change > 0]
    flaps = sum(1 for up in ups if any(up - FLAP_WINDOW_S <= down < up for down in downs))
    return {
        "requests": len(run.ttft),
        "ttft_p50_ms": percentile(ttft, 0.50) * 1000,
        "ttft_p95_ms": percentile(ttft, 0.95) * 1000,
        "ttft_p99_ms": percentile(ttft, 0.99) * 1000,
        "latency_p95_s": percentile(sorted(run.latency), 0.95),
        "goodput": good / len(ttft),
        "unhealthy_s": unhealthy,
        "replica_seconds": run.replica_seconds,
        "mean_replicas": run.replica_seconds / run.duration_s,
        "peak_replicas": run.peak_replicas,
        "max_queue": run.max_queue,
        "scale_ups": len(ups),
        "scale_downs": len(downs),
        "flaps": flaps,
        "replica_seconds_per_good_request": run.replica_seconds / good if good else float("inf"),
    }
