"""The Markdown report for one dataset, built only from its saved results so it can be regenerated exactly."""
from __future__ import annotations

import math
import statistics

# key, label, formatter, which direction is better (None: shown, never ranked)
METRICS = [
    ("ttft_p50_ms", "TTFT p50 (ms)", lambda v: f"{v:,.0f}", "lower"),
    ("ttft_p95_ms", "TTFT p95 (ms)", lambda v: f"{v:,.0f}", "lower"),
    ("ttft_p99_ms", "TTFT p99 (ms)", lambda v: f"{v:,.0f}", "lower"),
    ("goodput", "Goodput (TTFT within the objective)", lambda v: f"{v * 100:.1f}%", "higher"),
    ("unhealthy_s", "Seconds the service was unhealthy", lambda v: f"{v:,.0f}", "lower"),
    ("replica_seconds", "Replica-seconds (cost)", lambda v: f"{v:,.0f}", "lower"),
    ("replica_seconds_per_good_request", "Replica-seconds per good request", lambda v: "∞" if math.isinf(v) else f"{v:,.2f}", "lower"),
    ("mean_replicas", "Mean replicas", lambda v: f"{v:.1f}", None),
    ("peak_replicas", "Peak replicas", lambda v: f"{v:,.0f}", None),
    ("max_queue", "Longest queue (requests)", lambda v: f"{v:,.0f}", "lower"),
    ("scale_ups", "Scale-ups", lambda v: f"{v:,.0f}", None),
    ("scale_downs", "Scale-downs", lambda v: f"{v:,.0f}", None),
    ("flaps", "Flaps (a scale-up within 120 s of a scale-down)", lambda v: f"{v:,.0f}", None),
]
HELD = ["ttft_p95_ms", "goodput", "unhealthy_s", "replica_seconds", "replica_seconds_per_good_request"]


def by_policy(doc: dict) -> dict[str, dict[int, dict]]:
    table: dict[str, dict[int, dict]] = {p["label"]: {} for p in doc["policies"]}
    for row in doc["runs"]:
        table[row["policy"]][row["seed"]] = row
    return table


def better(a: float, b: float, direction: str) -> int:
    """1 when a is better than b, -1 when worse, 0 on a tie."""
    if a == b:
        return 0
    return 1 if (a < b) == (direction == "lower") else -1


def held(doc: dict, metric: str, direction: str) -> dict[str, list[str]]:
    """For each policy, the policies it beat in every run (and at least one run apiece, so a tie never counts)."""
    table = by_policy(doc)
    labels = list(table)
    seeds = sorted(next(iter(table.values())))
    wins: dict[str, list[str]] = {}
    for a in labels:
        beaten = []
        for b in labels:
            if a != b and all(better(table[a][s][metric], table[b][s][metric], direction) == 1 for s in seeds):
                beaten.append(b)
        if beaten:
            wins[a] = beaten
    return wins


def _cell(values: list[float], fmt, best: bool) -> str:
    median = statistics.median(values)
    lo, hi = min(values), max(values)
    text = fmt(median) if lo == hi else f"{fmt(median)} <sub>({fmt(lo)}–{fmt(hi)})</sub>"
    return f"**{text}**" if best else text


def markdown(doc: dict) -> str:
    table = by_policy(doc)
    labels = list(table)
    seeds = sorted(next(iter(table.values())))
    w = doc["workload"]
    requests = statistics.median(table[labels[0]][s]["requests"] for s in seeds)
    lines = [
        f"## {doc['title']}",
        "",
        f"Workload [{w['name']}](../../workloads/{w['name']}.json): {w['duration_s'] / 60:.0f} minutes, about {requests:,.0f} requests "
        f"in a run. The objective is a first token within {w['slo_ttft_s']:g} s. A pool may grow to "
        f"{doc['bounds']['max_replicas']} pods.",
        "",
        f"Each cell is the median of {len(seeds)} runs, with the lowest and highest in brackets. Every policy replays the "
        "same seeded trace in each run; the seeds differ between runs.",
        "",
        "| Policy | Spec | Fewest pods | Pod startup |",
        "|---|---|---|---|",
    ]
    for p in doc["policies"]:
        minimum = p.get("min_replicas", doc["bounds"]["min_replicas"])
        lines.append(f"| `{p['label']}` | `{p['text']}` | {minimum} | {p['startup_s']:g} s |")
    lines += ["", "| Metric | " + " | ".join(f"`{label}`" for label in labels) + " |", "|---|" + "---|" * len(labels)]
    for key, name, fmt, direction in METRICS:
        medians = {label: statistics.median(table[label][s][key] for s in seeds) for label in labels}
        best = None
        if direction:
            best = (min if direction == "lower" else max)(medians.values())
        cells = [_cell([table[label][s][key] for s in seeds], fmt, direction is not None and medians[label] == best)
                 for label in labels]
        hint = f" <sub>{direction} is better</sub>" if direction else ""
        lines.append(f"| {name}{hint} | " + " | ".join(cells) + " |")
    lines += ["", f"**Differences that held in every one of the {len(seeds)} runs**", "",
              "| Metric | Policy | Better than, in every run |", "|---|---|---|"]
    rows = 0
    names = {key: (name, direction) for key, name, _, direction in METRICS}
    for key in HELD:
        name, direction = names[key]
        for policy, beaten in held(doc, key, direction).items():
            lines.append(f"| {name} | `{policy}` | " + ", ".join(f"`{b}`" for b in beaten) + " |")
            rows += 1
    if not rows:
        lines.append("| none | | |")
    lines.append("")
    return "\n".join(lines)
