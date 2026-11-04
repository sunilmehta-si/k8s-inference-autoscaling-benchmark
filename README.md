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
> what the model includes, what it leaves out and what was chosen before the results. A cluster stage is the next step.

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

## The cluster stage

[`docs/cluster.md`](docs/cluster.md): the same policies on the same seeded traces on a kind cluster, with the real
Horizontal Pod Autoscaler, Prometheus and prometheus-adapter in front of simulated vLLM pods, so the model can be checked
against something that is not the model. `iab compare` sets each cluster run beside the simulation on the same seed and
settings. It runs in CI only: the scripts refuse any kubectl context but `kind-iab`.

The first comparison is [results/cluster](results/cluster/README.md): the `burst` workload, four policies, three seeds each,
twelve 30-minute runs. What it shows, and what it does not:

- **Medians and scaling decisions agree.** Median first-token latency is within 60 ms of the simulation for every policy,
  and `hpa-concurrency` and `hpa-queue` scale up as many times and to the same peak as the simulation.
- **The tail does not.** The 95th-percentile first-token latency is higher on the cluster than in the simulation in all 12 runs.
  Even `static-24`, which never scales, serves 97.7% within the objective on the cluster against 100% in the simulation.
  The likely cause is that each pod keeps its own queue behind the Service, while the simulation has one shared queue.
  That is a hypothesis; it has not been tested yet.
- **The signal ranking changes.** The simulation puts `hpa-utilization` second and `hpa-queue` last. On the cluster
  `hpa-queue` is second (70.3%) and `hpa-utilization` last (40.9%, peak 26 to 28 pods instead of 32). Why the cluster's
  utilization signal under-scales is not explained yet, so treat the simulation's ranking of that policy with caution.

## Status

The simulation, its seven datasets, the cluster stage's runner and comparison, and the first cluster dataset are built.
Not yet built: a per-pod queue in the simulation, to test the tail gap; an explanation of the utilization gap; KEDA reading the same signals, a predictive policy,
and a workload with a gentler ramp, to find where reactive scaling is enough.

## Related projects

- [k8s-inference-routing-benchmark](https://github.com/sunilmehta-si/k8s-inference-routing-benchmark): which router should sit in front of vLLM pods, measured on a kind cluster.
- [k8s-gpu-scheduler-benchmark](https://github.com/sunilmehta-si/k8s-gpu-scheduler-benchmark): which Kubernetes GPU scheduler packs the work best.
- [kubernetes-secure-mlops-pipeline](https://github.com/sunilmehta-si/kubernetes-secure-mlops-pipeline): the pipeline that ships a model to production safely.
- [agentic-code-review-tool](https://github.com/sunilmehta-si/agentic-code-review-tool): reviews every pull request here.

## License

MIT, see [LICENSE](LICENSE).
