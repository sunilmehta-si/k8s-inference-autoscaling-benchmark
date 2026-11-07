## A ramp from 3 to 20 requests per second over 600 s

Workload [ramp-600](../../workloads/ramp-600.json): 25 minutes, about 14,914 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization` | 2 | 45 s | 15 s |
| `cluster-like` | `cluster-like=hpa-concurrency:route=pod,lag=30` | 2 | 45 s | 15 s |

| Metric | `static-24` | `hpa-concurrency` | `hpa-utilization` | `cluster-like` |
|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **186 <sub>(184–189)</sub>** | 221 <sub>(216–225)</sub> | 209 <sub>(204–212)</sub> | 254 <sub>(243–267)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **635 <sub>(612–645)</sub>** | 893 <sub>(800–1,124)</sub> | 747 <sub>(718–837)</sub> | 3,572 <sub>(3,107–4,263)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,020 <sub>(1,020–1,050)</sub>** | 1,774 <sub>(1,276–4,667)</sub> | 1,261 <sub>(1,212–1,986)</sub> | 8,717 <sub>(6,130–10,072)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 99.2% <sub>(96.7%–99.9%)</sub> | 99.6% <sub>(99.0%–99.9%)</sub> | 91.1% <sub>(90.5%–91.8%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 60 <sub>(20–110)</sub> | 30 <sub>(10–60)</sub> | 510 <sub>(400–580)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 36,000 | **17,708 <sub>(16,505–19,901)</sub>** | 19,886 <sub>(19,065–20,552)</sub> | 19,922 <sub>(18,750–21,615)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.41 <sub>(2.40–2.45)</sub> | **1.20 <sub>(1.11–1.39)</sub>** | 1.34 <sub>(1.28–1.40)</sub> | 1.46 <sub>(1.40–1.59)</sub> |
| Mean replicas | 24.0 | 11.8 <sub>(11.0–13.3)</sub> | 13.3 <sub>(12.7–13.7)</sub> | 13.3 <sub>(12.5–14.4)</sub> |
| Peak replicas | 24 | 18 <sub>(16–20)</sub> | 21 <sub>(19–22)</sub> | 20 <sub>(19–26)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 22 <sub>(14–61)</sub> | 14 <sub>(9–27)</sub> | 58 <sub>(33–73)</sub> |
| Scale-ups | 0 | 8 <sub>(6–9)</sub> | 8 <sub>(7–10)</sub> | 8 <sub>(7–10)</sub> |
| Scale-downs | 0 | 2 <sub>(1–4)</sub> | 2 <sub>(1–3)</sub> | 2 <sub>(0–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 2 <sub>(0–3)</sub> | 0 <sub>(0–4)</sub> | 0 <sub>(0–5)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `hpa-utilization`, `cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `cluster-like` |
| TTFT p95 (ms) | `hpa-utilization` | `hpa-concurrency`, `cluster-like` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `hpa-utilization`, `cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `cluster-like` |
| Goodput (TTFT within the objective) | `hpa-utilization` | `hpa-concurrency`, `cluster-like` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `hpa-utilization`, `cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `cluster-like` |
| Seconds the service was unhealthy | `hpa-utilization` | `cluster-like` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `hpa-utilization` |
| Replica-seconds (cost) | `hpa-utilization` | `static-24` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `hpa-utilization`, `cluster-like` |
| Replica-seconds per good request | `hpa-utilization` | `static-24`, `cluster-like` |
| Replica-seconds per good request | `cluster-like` | `static-24` |
