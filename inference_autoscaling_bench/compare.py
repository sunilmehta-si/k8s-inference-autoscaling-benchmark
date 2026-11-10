"""Set the cluster's runs beside the simulation's, seed by seed.

The simulation is run here, not read from a file: for each cluster run it gets the same workload, the same seed (so the
same trace), the same policy and the same pod startup, minimum, maximum and scale-down window the cluster was given. Any
difference is then the model's, not the setup's. It is run four times: with one shared queue, the default; with a queue
per pod (`route=pod`), which is closer to a Kubernetes Service; with a queue per pod and the cluster's metrics lag
(`lag=METRICS_LAG_S`): Prometheus scrapes every 15 s and the recording rules the adapter serves are evaluated every 15 s,
so the autoscaler acts on a signal up to 30 s old (deploy/monitoring.yaml; a test holds the two together); and with a
queue per pod and that pipeline modelled piece by piece (`scrape=SCRAPE_S`): each pod scraped every 15 s at its own
offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from . import report
from .experiment import run_matrix
from .policies import Bounds
from .spec import parse
from .workload import Workload

METRICS_LAG_S = 30.0   # scrape interval + rule evaluation interval in deploy/monitoring.yaml
SCRAPE_S = 15.0        # the scrape interval, which is also the rule evaluation interval, in deploy/monitoring.yaml
MODELS = ("simulation", "simulation_pods", "simulation_lag", "simulation_scrape")

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


def autoscaled(policy: str) -> bool:
    """Whether a policy has an autoscaler, and so a scale-down window: the HPA's or the one KEDA creates."""
    return policy.startswith(("hpa-", "keda-"))


# Which way is better for the metrics that have one: +1 higher, -1 lower. The others (pods, scaling events) are reported
# as higher or lower without a verdict.
BETTER = {"goodput": 1, "ttft_p50_ms": -1, "ttft_p95_ms": -1, "ttft_p99_ms": -1, "unhealthy_s": -1, "replica_seconds": -1}


def pairs(doc: dict) -> list[tuple[str, list[dict], list[dict]]]:
    """(signal, HPA rows, KEDA rows) for every signal run both ways, on the seeds both ran, in seed order."""
    out = []
    for policy in sorted({r["policy"] for r in doc["rows"] if r["policy"].startswith("keda-")}):
        signal = policy[len("keda-"):]
        keda = {r["seed"]: r for r in doc["rows"] if r["policy"] == policy}
        hpa = {r["seed"]: r for r in doc["rows"] if r["policy"] == f"hpa-{signal}"}
        seeds = sorted(keda.keys() & hpa.keys())
        if seeds:
            out.append((signal, [hpa[s] for s in seeds], [keda[s] for s in seeds]))
    return out


def _seed_by_seed(hpa: list[float], keda: list[float], key: str) -> str:
    n = len(hpa)
    if key in BETTER:
        better = sum((k - h) * BETTER[key] > 0 for h, k in zip(hpa, keda))
        worse = sum((k - h) * BETTER[key] < 0 for h, k in zip(hpa, keda))
        return f"KEDA better in {better}, worse in {worse} of {n}"
    higher = sum(k > h for h, k in zip(hpa, keda))
    lower = sum(k < h for h, k in zip(hpa, keda))
    return f"KEDA higher in {higher}, lower in {lower} of {n}"


def keda_section(doc: dict) -> list[str]:
    """KEDA against the HPA on the cluster, signal by signal and seed by seed: the same signal, target, bounds and
    window, so a difference is the path the signal takes. Empty when no signal was run both ways."""
    found = pairs(doc)
    if not found:
        return []
    lines = ["### KEDA against the HPA, on the cluster", "",
             "Each signal run both ways on the same seeds: the HPA reading a pods metric through prometheus-adapter, and "
             "the HPA KEDA creates reading the sum over the pods as an external metric. A seed counts as better or worse "
             "when its two runs differ at all.", ""]
    for signal, hpa, keda in found:
        lines += [f"#### {signal}", "", f"Seeds {', '.join(str(r['seed']) for r in hpa)}.", "",
                  "| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |", "|---|---|---|---|---|"]
        for key, name, fmt in COMPARED:
            h = [r["cluster"][key] for r in hpa]
            k = [r["cluster"][key] for r in keda]
            lines.append(f"| {name} | {_cell(h, fmt)} | {_cell(k, fmt)} | {_diff(k, h, key, fmt)} | {_seed_by_seed(h, k, key)} |")
        lines.append("")
    return lines


def load_cluster_runs(directory: str | Path) -> list[dict]:
    runs = [json.loads(p.read_text()) for p in sorted(Path(directory).glob("**/*.json"))]
    runs = [r for r in runs if r.get("summary", {}).get("source") == "cluster"]
    if not runs:
        raise ValueError(f"no cluster runs in {directory}")
    return runs


def simulate_like(run: dict, workload: Workload, pod_queues: bool = False, lag_s: float = 0.0, scrape_s: float = 0.0) -> dict:
    """The simulation's summary for the cluster run's policy, seed and settings."""
    cfg = run["config"]
    policy = run["summary"]["policy"]
    options = (f"startup={cfg['startup_s']:g}" + (f",down={cfg['down_window_s']:g}" if autoscaled(policy) else "")
               + (",route=pod" if pod_queues else "") + (f",lag={lag_s:g}" if lag_s else "") + (f",scrape={scrape_s:g}" if scrape_s else ""))
    spec = parse(f"{policy}:{options}")
    rows, _ = run_matrix(workload, [spec], [run["summary"]["seed"]], Bounds(cfg["min_replicas"], cfg["max_replicas"]))
    return {k: v for k, v in rows[0].items() if k not in ("policy", "seed")}


def models(run: dict, workload: Workload) -> dict[str, dict]:
    """The four models' summaries for one cluster run."""
    return {"simulation": simulate_like(run, workload),
            "simulation_pods": simulate_like(run, workload, pod_queues=True),
            "simulation_lag": simulate_like(run, workload, pod_queues=True, lag_s=METRICS_LAG_S),
            "simulation_scrape": simulate_like(run, workload, pod_queues=True, scrape_s=SCRAPE_S)}


def build(title: str, workload: Workload, cluster_runs: list[dict]) -> dict:
    rows = []
    for run in sorted(cluster_runs, key=lambda r: (r["summary"]["policy"], r["summary"]["seed"])):
        summary = {k: v for k, v in run["summary"].items() if k not in ("policy", "seed", "source")}
        rows.append({"policy": run["summary"]["policy"], "seed": run["summary"]["seed"], "config": run["config"],
                     "cluster": summary, **models(run, workload), "client": run["client"], "events": run["events"]})
    return {"title": title, "workload": {"name": workload.name, "duration_s": workload.duration_s, "slo_ttft_s": workload.slo_ttft_s},
            "rows": rows}


def rebuild(doc: dict, workload: Workload) -> dict:
    """The comparison with its models run again: the cluster's side is kept, the simulation's side is recomputed, so a
    change to the model (or a new one) reaches a committed comparison without the cluster's raw runs."""
    if doc["workload"]["name"] != workload.name:
        raise ValueError(f"the comparison is of {doc['workload']['name']}, not {workload.name}")
    rows = []
    for row in doc["rows"]:
        run = {"config": row["config"], "summary": {"policy": row["policy"], "seed": row["seed"]}}
        kept = {k: v for k, v in row.items() if k not in MODELS}
        rows.append({**kept, **models(run, workload)})
    return {**doc, "rows": rows}


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
             "prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: "
             "one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it "
             "arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal "
             f"as it was {METRICS_LAG_S:g} s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a "
             f"queue per pod and that pipeline piece by piece: each pod scraped every {SCRAPE_S:g} s at its own offset, a rule "
             f"evaluated every {SCRAPE_S:g} s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the "
             "median over the seeds, with the lowest and highest in brackets.", ""]
    for policy in policies:
        rows = [r for r in doc["rows"] if r["policy"] == policy]
        cfg = rows[0]["config"]
        lines += [f"### `{policy}`", "",
                  f"{len(rows)} {'seed' if len(rows) == 1 else 'seeds'} ({', '.join(str(r['seed']) for r in rows)}). Pods start in {cfg['startup_s']:g} s"
                  + (f", scale-down window {cfg['down_window_s']:g} s" if autoscaled(policy) else "") + ".", "",
                  "| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped "
                  "| Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag "
                  "| Cluster minus queue per pod, scraped |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for key, name, fmt in COMPARED:
            c = [r["cluster"][key] for r in rows]
            sides = [[r[m][key] for r in rows] for m in MODELS]
            lines.append(f"| {name} | {_cell(c, fmt)} | " + " | ".join(_cell(v, fmt) for v in sides) + " | "
                         + " | ".join(_diff(c, v, key, fmt) for v in sides) + " |")
        failed = sum(r["client"]["failed"] for r in rows)
        lines += ["", f"Requests the cluster did not answer: {failed:,} of {sum(r['client']['requests'] for r in rows):,}.", ""]
    lines += keda_section(doc)
    lines += ["### Run by run", "", "| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag "
              "| Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod "
              "| TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in doc["rows"]:
        sides = [r["cluster"]] + [r[m] for m in MODELS]
        lines.append(f"| `{r['policy']}` | {r['seed']} | " + " | ".join(f"{x['goodput'] * 100:.1f}%" for x in sides) + " | "
                     + " | ".join(f"{x['ttft_p95_ms']:,.0f}" for x in sides)
                     + f" | {r['cluster']['peak_replicas']:,.0f} | {r['simulation']['peak_replicas']:,.0f} |")
    lines.append("")
    return "\n".join(lines)


def write(directory: str | Path, doc: dict) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "runs.json").write_text(json.dumps(doc, indent=1) + "\n")
    (directory / "README.md").write_text(markdown(doc))


def read(directory: str | Path) -> dict:
    return json.loads((Path(directory) / "runs.json").read_text())
