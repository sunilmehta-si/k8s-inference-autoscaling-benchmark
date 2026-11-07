# k8s-inference-autoscaling-benchmark

[![ci](https://github.com/sunilmehta-si/k8s-inference-autoscaling-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/sunilmehta-si/k8s-inference-autoscaling-benchmark/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.12%20%7C%203.13-3776ab)
![Dependencies](https://img.shields.io/badge/dependencies-none-green)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**What should a Kubernetes autoscaler follow when it scales LLM inference, and can it hold a latency objective at all?**
This project answers with numbers. It replays the same bursty chat trace through a model of a vLLM deployment, scaled by
the Kubernetes HorizontalPodAutoscaler's own algorithm on four signals (slot utilization, requests in the system, queue
depth, request rate), and measures what users feel (time to first token), what it costs (replica-seconds) and how the
autoscaler behaves (flapping, how long the service was unhealthy). **No GPUs, no cluster and no dependencies are
needed**, and every number is reproducible from a seed.

> **Status: a simulation.** The pod, the queue and the controller are modelled, not measured. The results compare
> settings against one another; they are not benchmarks of a real cluster. [The methodology](docs/methodology.md) says
> what the model includes, what it leaves out and what was chosen before the results. The cluster stage below checks
> the model against the real HPA on a kind cluster.

![Demand, pods and queue for each signal in the first run](results/signals/chart.svg)

## The short answer

On a thirty-minute trace with a ramp from 3 to 20 requests per second in 30 seconds and a spike to 40, with a 2 second
first-token objective:

- **No default autoscaler holds the objective.** The best signal, requests in the system, serves 80.3% of requests
  within 2 s. A static pool sized for the peak serves every one, at 24 pods all the time. The autoscaler costs 74% of
  that pool.
- **Requests in the system beat the other three signals at their pre-chosen targets**, in goodput in every one of
  eight runs, and had 1 flap where queue depth had 8. A different target moves a signal a long way,
  so this ranks four settings, not four signals ([why](docs/methodology.md#what-was-decided-before-the-results-and-what-changed-after)).
- **The miss is pod startup first and the delay in deciding second. It is not the target or the scale-up limit.** A
  target of 3 instead of 6 buys 5.5 points of goodput for 20% more cost, and lifting the HPA's +4 pods or doubling limit
  buys 2. Pods that start in 10 seconds instead of 45 buy 7, and deciding every second instead of every 15 buys 2
  more. Only pods that start in one second, with a decision every second, serve every request, at 62% of the static
  pool's cost. A ramp from 3 to 20 requests per second in 30 seconds builds a queue faster than a pod that takes tens
  of seconds to start can drain it, so faster pods (a cached image and model) are worth more than a cleverer signal.
- **Standing headroom is the cheapest lever.** Keeping at least 12 pods instead of 2 lifts goodput to 93.5% for about
  3% more replica-seconds, because the autoscaler scales up to the ceiling during the burst either way.
- **A shorter scale-down window saves a lot and costs a lot.** A 30 second window cuts cost by 41% and flaps 16 times,
  and goodput falls from 80.3% to 64.1%.

| Question | Policy | Goodput | Replica-seconds | Seconds unhealthy |
|---|---|---|---|---|
| [Signal](results/signals/README.md) | `static-24` | 100.0% | 43,200 | 0 |
| [Signal](results/signals/README.md) | `hpa-concurrency` | 80.3% | 32,053 | 215 |
| [Signal](results/signals/README.md) | `hpa-utilization` | 68.7% | 27,893 | 325 |
| [Signal](results/signals/README.md) | `hpa-queue` | 63.7% | 33,521 | 395 |
| [Signal](results/signals/README.md) | `hpa-rps` | 54.0% | 18,469 | 425 |
| [Lower target](results/targets/README.md) | `target-3` | 85.8% | 38,554 | 160 |
| [No scale-up limit](results/scale-up-limit/README.md) | `limit-none` | 82.5% | 32,252 | 175 |
| [10 s pod startup](results/startup/README.md) | `startup-10s` | 87.7% | 29,551 | 115 |
| [120 s pod startup](results/startup/README.md) | `startup-120s` | 64.5% | 34,901 | 420 |
| [Both of those lifts](results/scale-up-limit/README.md) | `limit-none-startup-10s` | 90.0% | 28,742 | 80 |
| [Pods and decisions in 1 s](results/sync-period/README.md) | `instant` | 100.0% | 26,933 | 0 |
| [At least 12 pods](results/warm-pool/README.md) | `min-12` | 93.5% | 33,076 | 65 |
| [30 s scale-down window](results/down-window/README.md) | `conc-down-30` | 64.1% | 18,817 | 430 |

Each cell is the median of eight runs; every run replays its own seeded trace through every policy. The tables behind
each row, with the range over the runs and the differences that held in every run, are in [`results/`](results/).
A test regenerates every table, chart and number on this page from the saved results.

## Policies

| Spec | What it is |
|---|---|
| `static-N` | A fixed pool of N pods. |
| `hpa-utilization` | The HPA on busy slots over slots, target 0.6. What GPU utilization stands in for. |
| `hpa-concurrency` | The HPA on requests in the system (running plus waiting) per pod, target 6. |
| `hpa-queue` | The HPA on requests waiting per pod, target 1. |
| `hpa-rps` | The HPA on requests per second over the last 30 s, per pod, target 1.4. |

Any spec takes options after a colon: `hpa-queue:target=2,down=60,startup=120,min=6`. `iab policies` lists them. The
targets were chosen before any run was compared and were not tuned; the datasets above show what changing one does.

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -e .      # no dependencies, Python 3.10 or later
iab trace workloads/burst.json                                         # what the trace looks like
iab run workloads/burst.json -p static-24 -p hpa-concurrency -p hpa-queue
iab matrix workloads/burst.json --runs 8 --out /tmp/mine -p hpa-concurrency -p "slow=hpa-concurrency:startup=120"
make test                                                              # the unit tests
make results                                                           # regenerate every dataset; git diff shows any change
```

`iab matrix` writes `runs.json` (every run), `README.md` (the tables) and `chart.svg`. `iab report DIR` renders the
last two again from `runs.json`. A workload is a JSON file of a rate schedule and two size distributions
([burst](workloads/burst.json), [smoke](workloads/smoke.json)); write another to try your own traffic.

## How it works

`workload.py` draws a trace from a rate schedule. `sim.py` is a discrete-event model of pods, slots, one queue and the
pod lifecycle. `policies.py` is the HPA algorithm, step by step, behind four signals. `metrics.py`, `report.py` and
`chart.py` turn runs into the numbers, tables and chart. Everything is deterministic: the same workload, seed and
policy give the same run on any machine and Python version, and the committed results are checked by re-running them.

## Where reactive scaling is enough

Every dataset above uses a ramp from 3 to 20 requests per second in 30 seconds. [`results/ramps`](results/ramps) asks
how slow a ramp must be for the HPA to keep up: four workloads that differ only in how long the same ramp takes (30, 120,
300 and 600 s), eight runs each, with `static-24`, `hpa-concurrency`, `hpa-utilization`, and `cluster-like`, which is
`hpa-concurrency` with a queue per pod and the 30 s metrics lag the cluster has (`make results-ramps`). The policies and
ramps were chosen before the runs.

- **In the model, a ten-minute ramp is slow enough.** `hpa-concurrency` serves 79.5%, 88.0%, 94.6% and 99.2% of
  requests in time on the four ramps (medians), more on each longer ramp in all eight runs, and at 600 s it costs
  46–55% of `static-24`.
- **The best signal depends on the ramp.** `hpa-utilization` is below `hpa-concurrency` on the 30 s and 120 s ramps
  and at or above it on the 300 s and 600 s ramps, in every run.
- **With the cluster's queue per pod and metrics lag, no ramp is slow enough.** `cluster-like` is below
  `hpa-concurrency` in every run on every ramp, and no run serves more than 91.8% in time, even at 600 s. Most of the
  gap is the queue per pod: on the 600 s ramp a queue per pod alone gives 93.2% and the lag alone 97.7% (medians). It
  is not random routing in itself, since `static-24` with a queue per pod serves 99.8%; it is random routing to pods the
  HPA keeps near its target of 6 requests on 8 slots, where one unlucky pod queues while another has room.

## The cluster stage

[`docs/cluster.md`](docs/cluster.md): the same policies on the same seeded traces on a kind cluster, with the real
Horizontal Pod Autoscaler, Prometheus and prometheus-adapter in front of simulated vLLM pods, so the model can be checked
against something that is not the model. `iab compare` sets each cluster run beside the simulation on the same seed and
settings. It runs in CI only: the scripts refuse any kubectl context but `kind-iab`.

The first comparison is [results/cluster](results/cluster/README.md): the `burst` workload, four policies, three seeds each,
twelve 30-minute runs. What it shows, and what it does not:

- **Medians and scaling decisions agree, for three policies.** The median first-token latency of `hpa-concurrency`,
  `hpa-queue` and `static-24` is within 60 ms of the simulation, and the first two scale up as many times and to the
  same peak. `hpa-utilization` is the exception: its median first token is 7.7 s on the cluster against 0.28 s in the
  simulation.
- **The tail is worse on the cluster in all 12 runs, and a queue per pod explains much of it.** The simulation's
  default is one shared queue. With `route=pod`, each request goes to a random ready pod and waits in that pod's own
  queue, as behind a Service, and a pod added later cannot take work already queued elsewhere. That moves the
  simulation toward the cluster for three policies: the median 95th-percentile first token of `hpa-concurrency` goes
  from 45 s to 85 s against 121 s on the cluster, `hpa-utilization` from 43 s to 81 s against 165 s, and `static-24`,
  which never scales, from 642 ms to 914 ms against 1,038 ms. For `hpa-queue` it overshoots: 115 s against 88 s.
  A queue per pod does not close the gap on its own.
- **The rest is mostly metrics lag.** The cluster's autoscaler reads each signal through Prometheus, which scrapes every
  15 s, and a recording rule evaluated every 15 s, so it acts on a value up to 30 s old; the simulation saw the exact
  state. With a queue per pod and `lag=30`, the median goodput of every HPA policy is within 3.2 points of the cluster
  (`hpa-concurrency` 75.1% against 76.4%, `hpa-queue` 73.5% against 70.3%, `hpa-utilization` 38.3% against 40.9%), and
  the median 95th-percentile first token of `hpa-concurrency` is 121 s on both. The tail of `hpa-utilization` is still
  shorter in the model (131 s against 165 s). The 30 s comes from the configuration, and a test holds the two together;
  lags of 15 and 45 s fit goodput less well for `hpa-concurrency` and `hpa-utilization`. `static-24` never scales, so
  lag cannot move it, and its remaining 124 ms at the 95th percentile is not explained.
- **A queue per pod also gives the cluster's ranking of the signals.** With one shared queue the simulation puts
  `hpa-utilization` second (72.3%) and `hpa-queue` last (64.3%). With a queue per pod it puts `hpa-queue` second (79.9%)
  and `hpa-utilization` last (56.2%), as on the cluster (70.3% and 40.9%), and `hpa-utilization` has a median peak of 26 pods, as
  on the cluster, instead of 32. So the earlier ranking of `hpa-utilization` came from the shared queue, not from the
  signal. The cluster is still worse than either model for that policy, by 15 points of goodput against the queue per pod.

The seven datasets above were run with one shared queue. [`results/pod-queues`](results/pod-queues/README.md) runs them
again with a queue per pod, as behind a Service: pod startup is still the biggest lever, but requests in the system no
longer clearly beat queue depth, standing headroom helps half as much, and a shorter scale-down window saves less.

## Status

The simulation, its seven datasets, the cluster stage's runner and comparison, the first cluster dataset, and a model
with a queue per pod and the cluster's metrics lag that matches its goodput within 3.2 points, and four ramps that show
where reactive scaling is enough are built. Not yet built:
an explanation of what is left of `hpa-utilization`'s tail on the cluster; KEDA reading the same signals, a predictive
policy, and the ramps on the cluster.

## Related projects

- [k8s-inference-routing-benchmark](https://github.com/sunilmehta-si/k8s-inference-routing-benchmark): which router should sit in front of vLLM pods, measured on a kind cluster.
- [k8s-gpu-scheduler-benchmark](https://github.com/sunilmehta-si/k8s-gpu-scheduler-benchmark): which Kubernetes GPU scheduler packs the work best.
- [kubernetes-secure-mlops-pipeline](https://github.com/sunilmehta-si/kubernetes-secure-mlops-pipeline): the pipeline that ships a model to production safely.
- [agentic-code-review-tool](https://github.com/sunilmehta-si/agentic-code-review-tool): reviews every pull request here.

## License

MIT, see [LICENSE](LICENSE).
