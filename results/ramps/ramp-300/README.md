## A ramp from 3 to 20 requests per second over 300 s

Workload [ramp-300](../../workloads/ramp-300.json): 20 minutes, about 11,492 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization` | 2 | 45 s | 15 s |
| `cluster-like` | `cluster-like=hpa-concurrency:route=pod,lag=30` | 2 | 45 s | 15 s |

| Metric | `static-24` | `hpa-concurrency` | `hpa-utilization` | `cluster-like` |
|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **187 <sub>(184–189)</sub>** | 222 <sub>(208–226)</sub> | 211 <sub>(204–220)</sub> | 230 <sub>(224–257)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **632 <sub>(610–646)</sub>** | 2,286 <sub>(1,276–3,653)</sub> | 893 <sub>(760–1,608)</sub> | 10,098 <sub>(4,049–15,917)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,027 <sub>(1,020–1,055)</sub>** | 5,004 <sub>(2,534–9,041)</sub> | 2,143 <sub>(1,212–6,306)</sub> | 24,133 <sub>(11,137–40,375)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 94.6% <sub>(92.1%–97.5%)</sub> | 98.9% <sub>(95.5%–99.7%)</sub> | 89.5% <sub>(87.9%–91.8%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 100 <sub>(70–120)</sub> | 55 <sub>(20–90)</sub> | 290 <sub>(270–320)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 28,800 | **16,536 <sub>(15,024–18,497)</sub>** | 17,018 <sub>(15,885–17,940)</sub> | 20,585 <sub>(15,834–22,007)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.51 <sub>(2.46–2.55)</sub> | 1.52 <sub>(1.34–1.73)</sub> | **1.51 <sub>(1.37–1.57)</sub>** | 1.99 <sub>(1.54–2.17)</sub> |
| Mean replicas | 24.0 | 13.8 <sub>(12.5–15.4)</sub> | 14.2 <sub>(13.2–14.9)</sub> | 17.2 <sub>(13.2–18.3)</sub> |
| Peak replicas | 24 | 22 <sub>(17–31)</sub> | 21 <sub>(19–25)</sub> | 32 <sub>(20–32)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 84 <sub>(32–119)</sub> | 32 <sub>(16–72)</sub> | 178 <sub>(67–258)</sub> |
| Scale-ups | 0 | 7 <sub>(5–9)</sub> | 7 <sub>(5–9)</sub> | 8 <sub>(6–10)</sub> |
| Scale-downs | 0 | 2 <sub>(1–4)</sub> | 2 <sub>(0–4)</sub> | 3 <sub>(2–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 <sub>(0–1)</sub> | 0 | 0 <sub>(0–2)</sub> |

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
| Seconds the service was unhealthy | `hpa-utilization` | `hpa-concurrency`, `cluster-like` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24` |
| Replica-seconds (cost) | `hpa-utilization` | `static-24` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24` |
| Replica-seconds per good request | `hpa-utilization` | `static-24`, `cluster-like` |
| Replica-seconds per good request | `cluster-like` | `static-24` |
