## A ramp from 3 to 20 requests per second over 120 s

Workload [ramp-120](../../workloads/ramp-120.json): 17 minutes, about 9,429 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization` | 2 | 45 s | 15 s |
| `cluster-like` | `cluster-like=hpa-concurrency:route=pod,lag=30` | 2 | 45 s | 15 s |

| Metric | `static-24` | `hpa-concurrency` | `hpa-utilization` | `cluster-like` |
|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **188 <sub>(184–190)</sub>** | 216 <sub>(207–220)</sub> | 269 <sub>(243–295)</sub> | 259 <sub>(242–269)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **640 <sub>(616–661)</sub>** | 10,283 <sub>(5,319–14,509)</sub> | 16,897 <sub>(10,430–23,531)</sub> | 48,009 <sub>(29,922–63,280)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,037 <sub>(1,020–1,084)</sub>** | 13,016 <sub>(8,796–17,733)</sub> | 18,075 <sub>(11,191–24,162)</sub> | 71,755 <sub>(51,354–81,555)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 88.0% <sub>(85.9%–90.4%)</sub> | 74.5% <sub>(70.1%–79.3%)</sub> | 79.5% <sub>(76.5%–81.2%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 115 <sub>(100–130)</sub> | 185 <sub>(130–200)</sub> | 330 <sub>(270–370)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 24,480 | **17,381 <sub>(17,043–17,678)</sub>** | 17,790 <sub>(17,355–18,360)</sub> | 19,312 <sub>(19,170–19,785)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.60 <sub>(2.55–2.69)</sub> | **2.10 <sub>(2.04–2.16)</sub>** | 2.54 <sub>(2.38–2.71)</sub> | 2.58 <sub>(2.47–2.75)</sub> |
| Mean replicas | 24.0 | 17.0 <sub>(16.7–17.3)</sub> | 17.4 <sub>(17.0–18.0)</sub> | 18.9 <sub>(18.8–19.4)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 224 <sub>(154–367)</sub> | 371 <sub>(215–522)</sub> | 533 <sub>(467–699)</sub> |
| Scale-ups | 0 | 6 <sub>(5–7)</sub> | 6 <sub>(5–10)</sub> | 7 <sub>(5–7)</sub> |
| Scale-downs | 0 | 2 <sub>(2–4)</sub> | 2 <sub>(1–5)</sub> | 4 <sub>(2–5)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 | 0 | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `hpa-utilization`, `cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `cluster-like` |
| TTFT p95 (ms) | `hpa-utilization` | `cluster-like` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `hpa-utilization`, `cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-utilization`, `cluster-like` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `hpa-utilization`, `cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-utilization`, `cluster-like` |
| Seconds the service was unhealthy | `hpa-utilization` | `cluster-like` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `hpa-utilization`, `cluster-like` |
| Replica-seconds (cost) | `hpa-utilization` | `static-24`, `cluster-like` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `hpa-utilization`, `cluster-like` |
