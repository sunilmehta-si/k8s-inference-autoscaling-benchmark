"""iab: compare autoscaling policies for LLM inference on the same traces."""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from . import __version__, experiment, report, results, workload as workloads
from .metrics import summarize
from .policies import SIGNALS, Bounds
from .sim import simulate
from .spec import parse


def _specs(texts: list[str]):
    try:
        return [parse(t) for t in texts]
    except ValueError as err:
        raise SystemExit(f"iab: {err}") from None


def cmd_policies(args) -> int:
    print("static-N                a fixed pool of N pods")
    for name, (_, target) in SIGNALS.items():
        print(f"{'hpa-' + name:<24}the HPA on {name}, default target {target:g} per pod")
    print("\nA spec is [label=]policy[:key=value,...]. Keys: target, down, up_window, tolerance, up_pods, up_percent, startup, min, sync.")
    return 0


def cmd_trace(args) -> int:
    w = workloads.load(args.workload)
    trace = workloads.generate(w, args.seed)
    prompts = [r.prompt_tokens for r in trace]
    outputs = [r.output_tokens for r in trace]
    print(f"{w.name}: {len(trace):,} requests in {w.duration_s:g} s (the schedule expects {w.expected_requests:,.0f}), "
          f"peak {w.peak_rate:g} requests/s")
    print(f"prompt tokens: median {statistics.median(prompts):,.0f}, mean {statistics.mean(prompts):,.0f}, max {max(prompts):,}")
    print(f"output tokens: median {statistics.median(outputs):,.0f}, mean {statistics.mean(outputs):,.0f}, max {max(outputs):,}")
    return 0


def cmd_run(args) -> int:
    w = workloads.load(args.workload)
    trace = workloads.generate(w, args.seed)
    bounds = Bounds(args.min_replicas, args.max_replicas)
    for spec in _specs(args.policy):
        own = bounds if spec.min_replicas is None else Bounds(spec.min_replicas, bounds.max_replicas)
        summary = summarize(simulate(trace, w, spec.make(), spec.replica, own, spec.sync_s), w)
        print(f"{spec.label}: " + ", ".join(f"{key} {fmt(summary[key])}" for key, _, fmt, _ in report.METRICS))
    return 0


def cmd_matrix(args) -> int:
    w = workloads.load(args.workload)
    specs = _specs(args.policy)
    bounds = Bounds(args.min_replicas, args.max_replicas)
    seeds = list(range(1, args.runs + 1))
    rows, kept = experiment.run_matrix(w, specs, seeds, bounds, keep_runs_for=seeds[0])
    doc = results.build(args.title or w.name, w, bounds, specs, rows, kept, workloads.generate(w, seeds[0]))
    results.write(args.out, doc)
    print(f"{len(rows)} runs written to {args.out}")
    return 0


def cmd_report(args) -> int:
    results.render(args.directory, results.read(args.directory))
    print(f"rendered {Path(args.directory) / 'README.md'} and chart.svg")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="iab", description=__doc__)
    parser.add_argument("--version", action="version", version=f"iab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("policies", help="list the policies and their options").set_defaults(func=cmd_policies)

    p = sub.add_parser("trace", help="summarise the trace a workload gives for a seed")
    p.add_argument("workload")
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(func=cmd_trace)

    def common(p):
        p.add_argument("workload")
        p.add_argument("-p", "--policy", action="append", required=True, metavar="SPEC", help="repeat for each policy")
        p.add_argument("--min-replicas", type=int, default=2)
        p.add_argument("--max-replicas", type=int, default=32)

    p = sub.add_parser("run", help="one seed, printed to the terminal")
    common(p)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("matrix", help="every policy on N seeded traces, written as results.json, README.md and chart.svg")
    common(p)
    p.add_argument("--runs", type=int, default=8)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.set_defaults(func=cmd_matrix)

    p = sub.add_parser("report", help="render README.md and chart.svg again from a dataset's runs.json")
    p.add_argument("directory")
    p.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError, RuntimeError) as err:
        print(f"iab: {err}", file=sys.stderr)
        return 1
