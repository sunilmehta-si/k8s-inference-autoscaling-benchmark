"""A dataset's saved results: one JSON document, and the README and chart that are rendered from it."""
from __future__ import annotations

import json
from pathlib import Path

from . import chart, report
from .policies import Bounds
from .sim import SYNC_PERIOD_S, Run
from .spec import Spec
from .workload import Request, Workload


def demand_series(trace: list[Request], duration_s: float) -> list[list[float]]:
    """Arrivals per second in each sync period, placed at the middle of the period."""
    bins = [0] * int(duration_s // SYNC_PERIOD_S)
    for request in trace:
        bins[min(int(request.arrival // SYNC_PERIOD_S), len(bins) - 1)] += 1
    return [[round(i * SYNC_PERIOD_S + SYNC_PERIOD_S / 2, 3), count / SYNC_PERIOD_S] for i, count in enumerate(bins)]


def build(title: str, workload: Workload, bounds: Bounds, specs: list[Spec], rows: list[dict], kept: dict[str, Run],
          first_trace: list[Request]) -> dict:
    return {
        "title": title,
        "workload": {"name": workload.name, "duration_s": workload.duration_s, "slo_ttft_s": workload.slo_ttft_s},
        "bounds": {"min_replicas": bounds.min_replicas, "max_replicas": bounds.max_replicas},
        "policies": [{"label": s.label, "text": s.text, "startup_s": s.replica.startup_s, "sync_s": s.sync_s,
                      "min_replicas": bounds.min_replicas if s.min_replicas is None else s.min_replicas} for s in specs],
        "runs": rows,
        "demand": demand_series(first_trace, workload.duration_s),
        "timelines": {label: [list(row) for row in run.timeline] for label, run in kept.items()},
    }


def write(directory: str | Path, doc: dict) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "runs.json").write_text(json.dumps(doc, indent=1) + "\n")
    render(directory, doc)


def render(directory: str | Path, doc: dict) -> None:
    directory = Path(directory)
    (directory / "README.md").write_text(report.markdown(doc))
    (directory / "chart.svg").write_text(chart.svg(doc))


def read(directory: str | Path) -> dict:
    return json.loads((Path(directory) / "runs.json").read_text())
