"""A workload is a request-rate schedule and two size distributions; a seed turns it into one exact request trace.

The rate between two schedule points is linear, so a ramp is a ramp and a spike is two points a few seconds apart.
Arrivals are a non-homogeneous Poisson process, drawn by thinning, and the sizes are log-normal, which is the usual
shape of prompt and completion lengths. The same workload and seed give the same trace on every machine and Python.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from random import Random


@dataclass(frozen=True)
class Request:
    index: int
    arrival: float
    prompt_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Workload:
    name: str
    description: str
    duration_s: float
    schedule: tuple[tuple[float, float], ...]  # (second, requests per second), linear in between
    prompt_median: float
    prompt_sigma: float
    prompt_max: int
    output_median: float
    output_sigma: float
    output_max: int
    slo_ttft_s: float

    def rate_at(self, t: float) -> float:
        points = self.schedule
        if t <= points[0][0]:
            return points[0][1]
        for (t0, r0), (t1, r1) in zip(points, points[1:]):
            if t <= t1:
                return r0 if t1 == t0 else r0 + (r1 - r0) * (t - t0) / (t1 - t0)
        return points[-1][1]

    @property
    def peak_rate(self) -> float:
        return max(rate for _, rate in self.schedule)

    @property
    def expected_requests(self) -> float:
        """The area under the schedule: what the trace averages over many seeds."""
        return sum((t1 - t0) * (r0 + r1) / 2 for (t0, r0), (t1, r1) in zip(self.schedule, self.schedule[1:]))


def from_dict(data: dict) -> Workload:
    schedule = tuple((float(t), float(r)) for t, r in data["schedule"])
    if len(schedule) < 2:
        raise ValueError("a schedule needs at least two points")
    times = [t for t, _ in schedule]
    if times[0] != 0 or times != sorted(times):
        raise ValueError("schedule times must start at 0 and not go backwards")
    if any(r < 0 for _, r in schedule) or max(r for _, r in schedule) <= 0:
        raise ValueError("schedule rates must be non-negative and not all zero")
    duration = float(data["duration_s"])
    if times[-1] != duration:
        raise ValueError(f"the schedule ends at {times[-1]}, not at the duration {duration}")
    sizes = data["prompt_tokens"], data["output_tokens"]
    return Workload(
        name=data["name"], description=data["description"], duration_s=duration, schedule=schedule,
        prompt_median=float(sizes[0]["median"]), prompt_sigma=float(sizes[0]["sigma"]), prompt_max=int(sizes[0]["max"]),
        output_median=float(sizes[1]["median"]), output_sigma=float(sizes[1]["sigma"]), output_max=int(sizes[1]["max"]),
        slo_ttft_s=float(data["slo_ttft_s"]),
    )


def load(path: str | Path) -> Workload:
    return from_dict(json.loads(Path(path).read_text()))


def generate(workload: Workload, seed: int) -> list[Request]:
    """The trace for `seed`: arrivals by thinning against the peak rate, then each accepted arrival's sizes."""
    rng = Random(seed)
    peak = workload.peak_rate
    trace: list[Request] = []
    t = 0.0
    while True:
        t += rng.expovariate(peak)
        if t >= workload.duration_s:
            return trace
        if rng.random() * peak > workload.rate_at(t):
            continue
        prompt = _size(rng, workload.prompt_median, workload.prompt_sigma, workload.prompt_max)
        output = _size(rng, workload.output_median, workload.output_sigma, workload.output_max)
        trace.append(Request(len(trace), t, prompt, output))


def _size(rng: Random, median: float, sigma: float, cap: int) -> int:
    return max(1, min(cap, round(math.exp(math.log(median) + sigma * rng.normalvariate(0, 1)))))
