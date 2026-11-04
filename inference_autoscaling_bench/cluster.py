"""Drive a run on the kind cluster and turn what it measured into the same numbers the simulation gives.

Everything here talks to the cluster through kubectl, and refuses any context but the benchmark's: a machine whose kubectl
points at a real cluster cannot be touched by mistake. The unit tests use a fake kubectl; a real run happens only in CI.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .client import Result
from .sim import Run
from .workload import Request, Workload

CONTEXT = "kind-iab"
NS = "iab"
MONITORING_NS = "monitoring"
SAMPLE_PERIOD_S = 5.0
FAILED_LATENCY_S = 3600.0   # a request that got no answer counts as having waited this long: far outside any objective


Runner = Callable[..., str]   # runner(args, input=None) -> stdout


def kubectl(args: list[str], input: str | None = None) -> str:
    done = subprocess.run(["kubectl", *args], input=input, capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise RuntimeError(f"kubectl {' '.join(args[:4])} failed: {done.stderr.strip()[:300]}")
    return done.stdout


def require_context(runner: Runner = kubectl) -> None:
    try:
        current = runner(["config", "current-context"]).strip()
    except RuntimeError:
        current = ""
    if current != CONTEXT:
        raise RuntimeError(f"refusing to run: kubectl context is {current!r}, not {CONTEXT!r}")


@dataclass
class Sample:
    t: float                  # epoch seconds
    ready: int
    pending: int              # pods that exist, are not terminating and are not ready
    terminating: int
    desired: int              # the Deployment's replica count, which the autoscaler sets
    running: float | None     # requests being served, from Prometheus (None when it could not be read)
    waiting: float | None


def count_pods(pods: dict) -> tuple[int, int, int]:
    """(ready, pending, terminating) from `kubectl get pods -o json`. Pods that finished are not counted."""
    ready = pending = terminating = 0
    for pod in pods.get("items", []):
        if pod.get("status", {}).get("phase") in ("Succeeded", "Failed"):
            continue
        if pod.get("metadata", {}).get("deletionTimestamp"):
            terminating += 1
        elif any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
            ready += 1
        else:
            pending += 1
    return ready, pending, terminating


def prometheus_value(runner: Runner, query: str) -> float | None:
    path = f"/api/v1/namespaces/{MONITORING_NS}/services/prometheus:9090/proxy/api/v1/query?query={urllib.parse.quote(query)}"
    try:
        result = json.loads(runner(["get", "--raw", path]))["data"]["result"]
        return float(result[0]["value"][1]) if result else 0.0
    except (RuntimeError, ValueError, KeyError, IndexError):
        return None


def take_sample(runner: Runner = kubectl, now: Callable[[], float] = time.time) -> Sample:
    pods = json.loads(runner(["-n", NS, "get", "pods", "-l", "app=sim", "-o", "json"]))
    desired = int(runner(["-n", NS, "get", "deployment", "sim", "-o", "jsonpath={.spec.replicas}"]) or 0)
    ready, pending, terminating = count_pods(pods)
    return Sample(now(), ready, pending, terminating, desired, prometheus_value(runner, "sum(vllm:num_requests_running)"),
                  prometheus_value(runner, "sum(vllm:num_requests_waiting)"))


@dataclass
class Collector:
    """Samples the cluster every `period_s` on a thread until stopped. A sample that fails is counted, not fatal."""
    runner: Runner = kubectl
    period_s: float = SAMPLE_PERIOD_S
    samples: list[Sample] = field(default_factory=list)
    failures: int = 0

    def __post_init__(self):
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                self.samples.append(take_sample(self.runner))
            except (RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
                self.failures += 1
            self._stop.wait(max(0.0, self.period_s - (time.monotonic() - started)))

    def start(self) -> "Collector":
        self._thread.start()
        return self

    def stop(self) -> list[Sample]:
        self._stop.set()
        self._thread.join(timeout=30)
        return self.samples


def build_run(policy: str, workload: Workload, trace: list[Request], results: list[Result], samples: list[Sample],
              start_epoch: float) -> Run:
    """The cluster's run in the simulation's own terms, so one metrics function summarises both.

    Requests that got no answer count as having waited FAILED_LATENCY_S, so they miss the objective and stay in the
    totals. Pod-seconds are integrated from the samples over the workload's own duration, as the simulation's cost is.
    The simulation's per-request wait is not measured on a cluster; it is filled with the time to first token."""
    ttft = [r.ttft_s if r.ok else FAILED_LATENCY_S for r in results]
    latency = [r.e2e_s if r.ok and r.e2e_s is not None else FAILED_LATENCY_S for r in results]
    ordered = sorted(samples, key=lambda s: s.t)
    timeline, events, replica_seconds, peak, max_queue = [], [], 0.0, 0, 0
    previous = None
    for sample in ordered:
        t = sample.t - start_epoch
        existing = sample.ready + sample.pending + sample.terminating
        peak = max(peak, existing)
        max_queue = max(max_queue, int(sample.waiting or 0))
        if t >= 0:
            timeline.append((round(t, 1), sample.ready, sample.pending, int(sample.running or 0), int(sample.waiting or 0)))
        if previous is not None:
            lo, hi = max(previous[0], 0.0), min(t, workload.duration_s)
            if hi > lo:
                replica_seconds += (hi - lo) * previous[1]   # a count holds until the next sample sees a change
            if sample.desired != previous[2] and 0 <= t <= workload.duration_s:
                events.append((round(t, 1), sample.desired - previous[2]))
        previous = (t, existing, sample.desired)
    if previous is not None and previous[0] < workload.duration_s:
        replica_seconds += (workload.duration_s - max(previous[0], 0.0)) * previous[1]
    return Run(policy, workload.name, workload.duration_s, [r.arrival for r in trace], list(ttft), ttft, latency, timeline,
               events, replica_seconds, peak, max_queue)


def job_state(runner: Runner, name: str = "client") -> str:
    """succeeded, failed or running."""
    status = json.loads(runner(["-n", NS, "get", "job", name, "-o", "json"])).get("status", {})
    if status.get("succeeded"):
        return "succeeded"
    if status.get("failed"):
        return "failed"
    return "running"


def wait_for_job(runner: Runner, timeout_s: float, poll_s: float = 10.0, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> str:
    deadline = clock() + timeout_s
    while True:
        state = job_state(runner)
        if state != "running":
            return state
        if clock() >= deadline:
            raise RuntimeError(f"the load client did not finish within {timeout_s:.0f} s")
        sleep(poll_s)


def parse_client_output(log: str) -> tuple[float, list[Result]]:
    """The client prints one JSON document as its last line: {"start_epoch": ..., "results": [...]}."""
    for line in reversed(log.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"results"' in line:
            data = json.loads(line)
            return float(data["start_epoch"]), [Result(**{k: v for k, v in r.items()}) for r in data["results"]]
    raise RuntimeError("the load client printed no results")


def write(path: str | Path, document: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(document, indent=1) + "\n")


def _job_manifest(seed: int, image: str, timeout_s: int) -> str:
    template = (Path(__file__).resolve().parent.parent / "deploy" / "client.yaml").read_text()
    return (template.replace("${SEED}", str(seed)).replace("${IMAGE}", image).replace("${DEADLINE_S}", str(timeout_s)))


def run_on_cluster(spec, workload: Workload, seed: int, workload_path: Path, image: str = "iab-client:dev",
                   runner: Runner = kubectl, period_s: float = SAMPLE_PERIOD_S) -> dict:
    """Replay the workload's trace for `seed` against the model servers, sampling the cluster as it goes.

    The servers, the monitoring and the autoscaler are already in place (scripts/run.sh puts them there)."""
    from .metrics import summarize
    from .workload import generate

    require_context(runner)
    trace = generate(workload, seed)
    runner(["-n", NS, "delete", "job", "client", "--ignore-not-found", "--wait=true"])
    configmap = runner(["-n", NS, "create", "configmap", "workload", f"--from-file=workload.json={workload_path}",
                        "--dry-run=client", "-o", "yaml"])
    runner(["apply", "-f", "-"], input=configmap)
    deadline = int(workload.duration_s * 2 + 900)
    runner(["apply", "-f", "-"], input=_job_manifest(seed, image, deadline))
    collector = Collector(runner, period_s).start()
    try:
        state = wait_for_job(runner, deadline)
    finally:
        samples = collector.stop()
    log = runner(["-n", NS, "logs", "job/client", "--tail=-1"])
    if state != "succeeded":
        raise RuntimeError(f"the load client {state}:\n{log[-2000:]}")
    start_epoch, results = parse_client_output(log)
    run = build_run(spec.label, workload, trace, results, samples, start_epoch)
    summary = summarize(run, workload)
    answered = [r for r in results if r.ok]
    summary.update({"policy": spec.label, "seed": seed, "source": "cluster"})
    return {
        "summary": summary,
        "client": {
            "requests": len(results), "answered": len(answered), "failed": len(results) - len(answered),
            "lateness_p95_s": sorted(r.lateness_s for r in results)[int(len(results) * 0.95)] if results else 0.0,
            "prompt_tokens_requested": sum(r.requested_prompt_tokens for r in results),
            "prompt_tokens_counted": sum(r.prompt_tokens or 0 for r in answered),
            "output_tokens_requested": sum(r.requested_output_tokens for r in answered),
            "output_tokens_counted": sum(r.completion_tokens or 0 for r in answered),
        },
        "sampling": {"samples": len(samples), "failures": collector.failures, "period_s": period_s},
        "timeline": [list(row) for row in run.timeline],
        "events": [list(e) for e in run.events],
    }
