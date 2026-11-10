# Changelog

## [Unreleased]

## [0.7.0] - 2026-11-10

KEDA beside the HPA on the cluster, and a third path that tells them apart. KEDA reads the same signals by its own
path, and the model predicted it would decide almost exactly as the HPA does. On the cluster no difference between the
paths held over two dispatches of the same seeds: KEDA led on utilization on every seed once and trailed on every seed
once. The first dispatch's reading, that the path made the difference, was withdrawn.

### Added
- KEDA as the other path to the same signals. `keda-concurrency`, `keda-queue` and `keda-utilization` run KEDA v2.21.0
  (release manifest by checksum, images by digest) in place of prometheus-adapter: a ScaledObject per signal in
  `deploy/keda/` sums the series Prometheus records and targets the HPA's value per pod, with the same bounds and
  scale-down window, which tests hold together. `scripts/deploy-keda.sh`, `scripts/apply-keda.sh`, `scripts/run.sh` and
  the cluster-run dispatch take them, and a `keda-smoke` job proves the path on a kind cluster.
- The simulation models the autoscaler KEDA creates: an external metric, the sum over the pods, averaged over every pod
  the Deployment has, ready or not, then the sum over the target (`Hpa(external=True)`, `keda-SIGNAL` specs).
- `iab compare` sets KEDA beside the HPA on the cluster, signal by signal and seed by seed, when a comparison holds both.
- `results/keda/model` (`make results-keda`): the model's prediction, committed before the cluster ran KEDA. The two
  controllers make the same decisions on concurrency in all eight seeds and differ in one seed on queue and three on
  utilization.
- `results/keda/cluster-burst`: the burst under the HPA and under KEDA on each signal on the cluster, three seeds each,
  in one dispatch. On utilization KEDA served more requests in time on every seed (48.2% against 40.6% at the median,
  first token 2.7 s against 12.7 s) for 7% more replica-seconds, where the model's arithmetic predicted 1.5 points. On
  concurrency and queue no difference held. The second dispatch below did not repeat the utilization lead.
- `results/keda/cluster-ramp-30`: the 30 s ramp under the HPA and under KEDA on concurrency and utilization, three seeds
  each. The burst's gain on utilization did not repeat: KEDA was worse on every seed, by 0.3, 7.5 and 1.3 points. On
  concurrency KEDA was better on two seeds and used fewer replica-seconds on all three.
- `external-concurrency`, `external-queue` and `external-utilization`: the HPA reading the signal's sum over the pods as
  an external metric from prometheus-adapter (`externalRules`, registered for the external metrics API only on clusters
  without KEDA): KEDA's arithmetic on the adapter's path. The cluster workflow's smoke job checks the path.
- `results/keda/cluster-burst-utilization`: the burst on utilization again, same seeds and settings, under the HPA, the
  external HPA and KEDA. It reversed the first dispatch: KEDA was below the HPA on every seed (41.3% against 43.4%), the
  external HPA at 44.0%, and KEDA's own runs moved 3.0 to 7.9 points between dispatches. The README withdraws the
  reading that the path made the difference; over both dispatches no difference between the paths holds.

### Changed
- A difference on the cluster is claimed only when it holds over more than one dispatch: three seeds on one dispatch
  share the same runners and hour, and utilization's goodput moved by up to 7.9 points between two dispatches of the
  same seed ([docs/methodology.md](docs/methodology.md)).
- The methodology no longer says there is no KEDA or that the cluster stage is still to come.

## [0.6.0] - 2026-11-08

The metrics pipeline modelled piece by piece, and all four ramps on the cluster. With each pod's sample given its own
age, the model places the utilization flip, and utilization's lead on the ten-minute ramp, where the cluster does;
the fixed 30 s lag, the pipeline's worst case, still fits requests in the system better.

### Added
- `scrape=S`, a model of the metrics pipeline piece by piece: each pod is scraped every S seconds at its own offset, a
  rule evaluated every S seconds at its own offset sums the latest sample of every pod, and the autoscaler reads the
  latest evaluation, so each pod's sample has its own age (0 to 2S) and a new pod's first sample arrives within S. It
  is not combined with `lag`. `iab compare` runs it as a fourth model (`scrape=15`, with a queue per pod) and the five
  committed comparisons carry its column; `iab recompare DIR --workload W` runs the models again for a committed
  comparison without the cluster's raw runs. On the ramps the sampled pipeline places the utilization flip and
  utilization's lead at 600 s where the cluster does, on every seed, and is within 11.9 points of the cluster for
  `hpa-utilization` on every seed (the fixed lag: 21.9); for `hpa-concurrency` it sits above the cluster on every ramp,
  where the fixed lag is closer. The README's ramp and cluster sections say so, and tests hold every number.
- `results/cluster-ramps` now holds all four ramps on the cluster (30 s and 300 s added), three seeds each. On the
  cluster no ramp is slow enough: `hpa-concurrency` serves 73.5%, 82.9%, 89.9% and 89.8%, below the one-queue model in
  every run, and its gain from a longer ramp stops at 300 s. The lagged model is within 5.6 points on every seed of
  every ramp and places the utilization flip where the cluster does (between 300 s and 600 s), where the one-queue
  model puts it at 300 s; it is below the cluster for `hpa-utilization` on every seed of every ramp. The README's ramp
  section and status say so, and tests hold every number.

## [0.5.0] - 2026-11-08

The ramps on the real cluster, and what is left of the utilization tail. On the cluster a ten-minute ramp is not slow
enough, as the lagged model said; the signal that wins depends on the ramp there too; and most of `hpa-utilization`'s
tail is the lag paid at every capped step.

### Added
- `results/cluster-ramps`: the 120 s and 600 s ramps on the kind cluster, three seeds each, with `static-24`,
  `hpa-concurrency` and `hpa-utilization`, compared with the three models. On the cluster a ten-minute ramp is not slow
  enough for `hpa-concurrency` (89.8% against 99.1% in the one-queue model), and the model with a queue per pod and the
  30 s lag is within 1.3 points on every seed. `hpa-utilization` beats `hpa-concurrency` on the 600 s ramp (94.2%
  against 89.8%) and loses on the 120 s ramp (50.5% against 82.9%), on every seed; the lagged model misses that lead by
  2.4–4.1 points. The README's ramp section and status say so, and tests hold every number.
- The README explains most of what is left of `hpa-utilization`'s tail on the cluster: utilization's ceiling of 1 caps
  each scale-up step, so the lag is paid at every step, and the model is four times as sensitive to 15 s more lag on
  utilization (+36 s at the 95th percentile) as on concurrency (+9 s). The cluster's tail sits at a 45 s lag and its
  goodput at 30 s, and most of the gap is one seed. Tests hold each number.

## [0.4.0] - 2026-11-07

Where reactive scaling is enough: the same deployment on ramps of 30 s to 10 minutes. In the model a ten-minute ramp is
slow enough; with the cluster's queue per pod and metrics lag, none is.

### Added
- `results/ramps` and `make results-ramps`: four workloads that differ only in how long one ramp from 3 to 20 requests
  per second takes (30, 120, 300 and 600 s), with `static-24`, `hpa-concurrency`, `hpa-utilization` and
  `cluster-like` (`hpa-concurrency` with a queue per pod and `lag=30`), eight runs each. In the model a ten-minute ramp
  is slow enough (99.2% in time at about half the static pool's cost); with a queue per pod and the lag no run gets
  above 91.8%, mostly because of random routing to pods kept near the target. The better signal flips from requests
  in the system to slot utilization at the 300 s ramp.

## [0.3.0] - 2026-11-07

Most of what was left of the gap between the cluster and the model is metrics lag: the real autoscaler acts on a signal
up to 30 s old, read through a Prometheus scrape and a recording rule.

### Added
- `lag` for any policy spec: the autoscaler acts on the signal (requests running and waiting, and the arrival rate) as
  it was at the latest sync at least that many seconds earlier, as when it reads it through Prometheus; pod counts
  stay current.
- `iab compare` runs a third model, a queue per pod with the cluster's 30 s metrics lag (Prometheus scrape interval
  plus recording-rule interval, held together by a test), and `results/cluster` shows it. With it the median goodput
  of every HPA policy is within 3.2 points of the cluster, and `hpa-concurrency`'s median p95 first token is 121 s on
  both. The README says what is still not explained.

## [0.2.0] - 2026-11-05

The model is checked against the real thing. Twelve 30-minute runs of the real Horizontal Pod Autoscaler, Prometheus and
prometheus-adapter on a kind cluster, in front of simulated vLLM pods, each set beside the simulation on the same seed.

### Added
- `results/cluster`: the `burst` workload, four policies, three seeds. Medians and the scaling decisions of
  `hpa-concurrency` and `hpa-queue` agree with the simulation; the 95th-percentile first token is higher on the cluster
  in all 12 runs; `hpa-utilization` does much worse on the cluster than with one shared queue (40.9% against 72.3%).
- `route=pod` for any policy spec: each request goes to a random ready pod when it arrives and waits in that pod's own
  queue, as behind a Kubernetes Service, instead of in one shared queue. It moves every policy toward the cluster (the
  p95 first token of `hpa-concurrency` goes from 45 s to 85 s against 121 s on the cluster, and `static-24` from 642 ms
  to 914 ms against 1,038 ms) and ranks the signals as the cluster does. What is left of the tail is not explained.
- `iab matrix --route pod` and `make results-pod-queues`: the seven datasets again with a queue per pod, in
  `results/pod-queues`. Pod startup stays the biggest lever; requests in the system beat queue depth in five of eight runs
  instead of eight; standing headroom lifts goodput by 6.1 points instead of 13.2; and with pods and decisions in one
  second 95.8% of requests are served in time, not every one.
- The cluster stage: `deploy/` (pinned kind, Prometheus and prometheus-adapter), `scripts/`, the `cluster` and
  `cluster-run` workflows, an open-loop load client and `iab cluster-run`. It runs in CI only; the scripts refuse any
  kubectl context but `kind-iab`.

### Changed
- `iab compare` runs the simulation twice, with one shared queue and with a queue per pod, and `results/cluster` shows
  both beside the cluster.
- The README no longer says the cluster's medians agree for every policy, because `hpa-utilization`'s do not (7.7 s
  against 0.28 s).

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
