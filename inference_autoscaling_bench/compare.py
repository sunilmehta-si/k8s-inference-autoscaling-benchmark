"""Set the cluster's runs beside the simulation's, seed by seed.

The simulation is run here, not read from a file: for each cluster run it gets the same workload, the same seed (so the
same trace), the same policy and the same pod startup, minimum, maximum and scale-down window the cluster was given. Any
difference is then the model's, not the setup's. It is run twice: with one shared queue, the default, and with a queue per
pod (`route=pod`), which is closer to a Kubernetes Service."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from . import report
from .experiment import run_matrix
from .policies import Bounds
from .spec import parse
from .workload import Workload

COMPARED = [
    ("goodput", "Goodput (TTFT within the objective)", lambda v: f"{v * 100:.1f}%"),
    ("ttft_p50_ms", "TTFT p50 (ms)", lambda v: f"{v:,.0f}"),
    ("ttft_p95_ms", "TTFT p95 (ms)", lambda v: f"{v:,.0f}"),
    ("ttft_p99_ms", "TTFT p99 (ms)", lambda v: f"{v:,.0f}"),
    ("unhealthy_s", "Seconds the service was unhealthy", lambda v: f"{v:,.0f}"),
    ("replica_seconds", "Replica-seconds (cost)", lambda v: f"{v:,.0f}"),
    ("peak_replicas", "Peak pods", lambda v: f"{v:,.0f}"),
    ("scale_ups", "Scale-ups", lambda v: f"{v:,.0f}"),
    ("scale_downs", "Scale-downs", lambda v: f"{v:,.0f}"),
    ("flaps", "Flaps", lambda v: f"{v:,.0f}"),
]


def load_cluster_runs(directory: str | Path) -> list[dict]:
    runs = [json.loads(p.read_text()) for p in sorted(Path(directory).glob("**/*.json"))]
    runs = [r for r in runs if r.get("summary", {}).get("source") == "cluster"]
    if not runs:
        raise ValueError(f"no cluster runs in {directory}")
    return runs


def simulate_like(run: dict, workload: Workload, pod_queues: bool = False) -> dict:
    """The simulation's summary for the cluster run's policy, seed and settings."""
    cfg = run["config"]
    policy = run["summary"]["policy"]
    options = (f"startup={cfg['startup_s']:g}" + (f",down={cfg['down_window_s']:g}" if policy.startswith("hpa-") else "")
               + (",route=pod" if pod_queues else ""))
    spec = parse(f"{policy}:{options}")
    rows, _ = run_matrix(workload, [spec], [run["summary"]["seed"]], Bounds(cfg["min_replicas"], cfg["max_replicas"]))
    return {k: v for k, v in rows[0].items() if k not in ("policy", "seed")}


def build(title: str, workload: Workload, cluster_runs: list[dict]) -> dict:
    rows = []
    for run in sorted(cluster_runs, key=lambda r: (r["summary"]["policy"], r["summary"]["seed"])):
        summary = {k: v for k, v in run["summary"].items() if k not in ("policy", "seed", "source")}
        rows.append({"policy": run["summary"]["policy"], "seed": run["summary"]["seed"], "config": run["config"],
                     "cluster": summary, "simulation": simulate_like(run, workload),
                     "simulation_pods": simulate_like(run, workload, pod_queues=True),
                     "client": run["client"], "events": run["events"]})
    return {"title": title, "workload": {"name": workload.name, "duration_s": workload.duration_s, "slo_ttft_s": workload.slo_ttft_s},
            "rows": rows}


def _cell(values: list[float], fmt) -> str:
    median = statistics.median(values)
    lo, hi = min(values), max(values)
    return fmt(median) if lo == hi else f"{fmt(median)} <sub>({fmt(lo)}–{fmt(hi)})</sub>"


def _diff(cluster: list[float], model: list[float], key: str, fmt) -> str:
    diff = statistics.median(cluster) - statistics.median(model)
    return ("+" if diff > 0 else "") + (fmt(diff) if key != "goodput" else f"{diff * 100:.1f} points")


def markdown(doc: dict) -> str:
    w = doc["workload"]
    policies = sorted({r["policy"] for r in doc["rows"]})
    lines = [f"## {doc['title']}", "",
             f"Workload [{w['name']}](../../workloads/{w['name']}.json), {w['duration_s'] / 60:.0f} minutes, objective a first token within "
             f"{w['slo_ttft_s']:g} s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and "
             "prometheus-adapter, simulated vLLM pods) and two runs of the simulation on the same trace with the same settings: "
             "one with a single shared queue, and one with a queue per pod, each request sent to a random ready pod when it "
             "arrives, as behind a Kubernetes Service. Each cell is the median over the seeds, with the lowest and highest in brackets.", ""]
    for policy in policies:
        rows = [r for r in doc["rows"] if r["policy"] == policy]
        cfg = rows[0]["config"]
        lines += [f"### `{policy}`", "",
                  f"{len(rows)} {'seed' if len(rows) == 1 else 'seeds'} ({', '.join(str(r['seed']) for r in rows)}). Pods start in {cfg['startup_s']:g} s"
                  + (f", scale-down window {cfg['down_window_s']:g} s" if policy.startswith("hpa-") else "") + ".", "",
                  "| Metric | Cluster | One shared queue | Queue per pod | Cluster minus one queue | Cluster minus queue per pod |",
                  "|---|---|---|---|---|---|"]
        for key, name, fmt in COMPARED:
            c = [r["cluster"][key] for r in rows]
            s = [r["simulation"][key] for r in rows]
            q = [r["simulation_pods"][key] for r in rows]
            lines.append(f"| {name} | {_cell(c, fmt)} | {_cell(s, fmt)} | {_cell(q, fmt)} | {_diff(c, s, key, fmt)} | {_diff(c, q, key, fmt)} |")
        failed = sum(r["client"]["failed"] for r in rows)
        lines += ["", f"Requests the cluster did not answer: {failed:,} of {sum(r['client']['requests'] for r in rows):,}.", ""]
    lines += ["### Run by run", "", "| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | Pods at peak, cluster | Pods at peak, simulation |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in doc["rows"]:
        c, s, q = r["cluster"], r["simulation"], r["simulation_pods"]
        lines.append(f"| `{r['policy']}` | {r['seed']} | {c['goodput'] * 100:.1f}% | {s['goodput'] * 100:.1f}% | {q['goodput'] * 100:.1f}% | "
                     f"{c['ttft_p95_ms']:,.0f} | {s['ttft_p95_ms']:,.0f} | {q['ttft_p95_ms']:,.0f} | {c['peak_replicas']:,.0f} | {s['peak_replicas']:,.0f} |")
    lines.append("")
    return "\n".join(lines)


def write(directory: str | Path, doc: dict) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "runs.json").write_text(json.dumps(doc, indent=1) + "\n")
    (directory / "README.md").write_text(markdown(doc))


def read(directory: str | Path) -> dict:
    return json.loads((Path(directory) / "runs.json").read_text())
