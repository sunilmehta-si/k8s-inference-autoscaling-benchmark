# Changelog

## [Unreleased]

### Added
- `route=pod` for any policy spec: each request goes to a random ready pod when it arrives and waits in that pod's own
  queue, as behind a Kubernetes Service, instead of in one shared queue. Run against the cluster's twelve runs, it moves
  every policy toward them (the p95 first token of `hpa-concurrency` goes from 45 s to 85 s against 121 s on the cluster,
  and `static-24` from 642 ms to 914 ms against 1,038 ms), so most of the tail gap is the queueing, not the autoscaler.
- `results/cluster`: twelve 30-minute runs on a kind cluster (the `burst` workload, four policies, three seeds), each
  beside the simulation on the same seed. Medians and the scaling decisions of `hpa-concurrency` and `hpa-queue` agree;
  the 95th-percentile first token is higher on the cluster in all 12 runs; `hpa-utilization` does much worse on the
  cluster than in the simulation (40.9% against 72.3%), which is not explained yet.

## [0.1.0] - 2026-11-04

The first release: a simulation of an LLM inference deployment behind the Kubernetes HorizontalPodAutoscaler, and what
it shows.

### Added
- `workload.py`: a rate schedule and log-normal size distributions, drawn as a non-homogeneous Poisson process into one
  exact trace per seed, with a test that the trace is the same on every Python version.
- `sim.py`: a discrete-event model of pods with slots, one queue, a pod startup delay, draining on scale-down and
  replica-second cost.
- `policies.py`: the HPA algorithm step by step (tolerance, the starting-pods correction, stabilization windows, the
  scale-up limit) behind four signals (slot utilization, requests in the system, queue depth, request rate), and static
  pools.
- `iab` with `policies`, `trace`, `run`, `matrix` and `report`, and a spec grammar with `target`, `down`, `up_window`,
  `tolerance`, `up_pods`, `up_percent`, `startup`, `min` and `sync`.
- Seven datasets of eight runs each (`make results`): which signal, which target, how long to wait before scaling
  down, how fast pods start, the scale-up limit, standing headroom and the decision period. Each has a table with the
  range over the runs, the differences that held in every run, and a chart.
- A README whose headline table and prose numbers are checked against the saved results, and a methodology that says
  what the model leaves out and what was decided before the results.
- CI on Python 3.10, 3.12 and 3.13, a job that regenerates every dataset and fails on any difference, Dependabot with
  a 14-day cooldown, and pull request review by agentic-code-review-tool.

### Changed
- The workload was lengthened from 10 to 30 minutes after a first look: a 10-minute trace cannot show scale-down against
  the HPA's 300 s window. No policy changed.
