"""Run every policy on the same traces, one trace per seed, and collect each run's metrics."""
from __future__ import annotations

from dataclasses import replace

from . import workload as workloads
from .metrics import summarize
from .policies import Bounds
from .sim import Run, simulate
from .spec import Spec


def run_matrix(workload: workloads.Workload, specs: list[Spec], seeds: list[int], bounds: Bounds = Bounds(),
               keep_runs_for: int | None = None) -> tuple[list[dict], dict[str, Run]]:
    """(rows, first-seed runs): a row of metrics per policy and seed, and the full run of the seed `keep_runs_for`."""
    if len({s.label for s in specs}) != len(specs):
        raise ValueError("two policies share a label")
    rows: list[dict] = []
    kept: dict[str, Run] = {}
    for seed in seeds:
        trace = workloads.generate(workload, seed)
        for spec in specs:
            own = bounds if spec.min_replicas is None else replace(bounds, min_replicas=spec.min_replicas)
            run = simulate(trace, workload, spec.make(), spec.replica, own)
            rows.append({"policy": spec.label, "seed": seed, **summarize(run, workload)})
            if seed == keep_runs_for:
                kept[spec.label] = run
    return rows, kept
