## Is the HPA's scale-up limit the bottleneck?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `limit-default` | `limit-default=hpa-concurrency` | 2 | 45 s | 15 s |
| `limit-8` | `limit-8=hpa-concurrency:up_pods=8,up_percent=200` | 2 | 45 s | 15 s |
| `limit-16` | `limit-16=hpa-concurrency:up_pods=16,up_percent=400` | 2 | 45 s | 15 s |
| `limit-none` | `limit-none=hpa-concurrency:up_pods=32` | 2 | 45 s | 15 s |
| `limit-none-startup-10s` | `limit-none-startup-10s=hpa-concurrency:up_pods=32,startup=10` | 2 | 10 s | 15 s |

| Metric | `static-24` | `limit-default` | `limit-8` | `limit-16` | `limit-none` | `limit-none-startup-10s` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **190 <sub>(185–192)</sub>** | 243 <sub>(236–252)</sub> | 240 <sub>(232–244)</sub> | 238 <sub>(232–242)</sub> | 238 <sub>(233–244)</sub> | 218 <sub>(217–224)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **643 <sub>(623–676)</sub>** | 47,125 <sub>(40,499–50,987)</sub> | 43,389 <sub>(38,200–49,630)</sub> | 42,258 <sub>(37,611–47,665)</sub> | 39,607 <sub>(36,778–42,401)</sub> | 11,444 <sub>(10,447–12,151)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 61,179 <sub>(57,387–64,283)</sub> | 54,035 <sub>(51,256–56,041)</sub> | 48,883 <sub>(46,376–50,588)</sub> | 46,477 <sub>(44,195–47,660)</sub> | 16,104 <sub>(15,235–16,993)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 80.3% <sub>(79.9%–81.7%)</sub> | 81.7% <sub>(81.3%–82.9%)</sub> | 82.4% <sub>(81.8%–83.0%)</sub> | 82.5% <sub>(81.9%–83.2%)</sub> | 90.0% <sub>(89.4%–90.6%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 215 <sub>(180–240)</sub> | 195 <sub>(160–230)</sub> | 185 <sub>(160–210)</sub> | 175 <sub>(150–210)</sub> | 80 <sub>(70–90)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | 32,053 <sub>(31,702–32,220)</sub> | 32,075 <sub>(31,756–32,644)</sub> | 32,255 <sub>(31,942–32,824)</sub> | 32,252 <sub>(31,876–32,645)</sub> | **28,742 <sub>(26,929–30,556)</sub>** |
| Replica-seconds per good request <sub>lower is better</sub> | 3.04 <sub>(3.00–3.06)</sub> | 2.79 <sub>(2.72–2.83)</sub> | 2.75 <sub>(2.69–2.82)</sub> | 2.75 <sub>(2.69–2.82)</sub> | 2.75 <sub>(2.68–2.80)</sub> | **2.25 <sub>(2.10–2.40)</sub>** |
| Mean replicas | 24.0 | 17.8 <sub>(17.6–17.9)</sub> | 17.8 <sub>(17.6–18.1)</sub> | 17.9 <sub>(17.7–18.2)</sub> | 17.9 <sub>(17.7–18.1)</sub> | 16.0 <sub>(15.0–17.0)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **18 <sub>(1–23)</sub>** | 838 <sub>(816–869)</sub> | 838 <sub>(816–869)</sub> | 838 <sub>(816–869)</sub> | 838 <sub>(816–869)</sub> | 758 <sub>(742–778)</sub> |
| Scale-ups | 0 | 10 <sub>(9–12)</sub> | 8 <sub>(7–10)</sub> | 8 <sub>(6–10)</sub> | 8 <sub>(4–9)</sub> | 6 <sub>(5–7)</sub> |
| Scale-downs | 0 | 7 <sub>(6–7)</sub> | 6 <sub>(5–7)</sub> | 6 <sub>(5–7)</sub> | 6 <sub>(5–8)</sub> | 7 <sub>(5–9)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `limit-default`, `limit-8`, `limit-16`, `limit-none`, `limit-none-startup-10s` |
| TTFT p95 (ms) | `limit-8` | `limit-default` |
| TTFT p95 (ms) | `limit-16` | `limit-default`, `limit-8` |
| TTFT p95 (ms) | `limit-none` | `limit-default`, `limit-8`, `limit-16` |
| TTFT p95 (ms) | `limit-none-startup-10s` | `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Goodput (TTFT within the objective) | `static-24` | `limit-default`, `limit-8`, `limit-16`, `limit-none`, `limit-none-startup-10s` |
| Goodput (TTFT within the objective) | `limit-8` | `limit-default` |
| Goodput (TTFT within the objective) | `limit-16` | `limit-default`, `limit-8` |
| Goodput (TTFT within the objective) | `limit-none` | `limit-default`, `limit-8`, `limit-16` |
| Goodput (TTFT within the objective) | `limit-none-startup-10s` | `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Seconds the service was unhealthy | `static-24` | `limit-default`, `limit-8`, `limit-16`, `limit-none`, `limit-none-startup-10s` |
| Seconds the service was unhealthy | `limit-8` | `limit-default` |
| Seconds the service was unhealthy | `limit-16` | `limit-default` |
| Seconds the service was unhealthy | `limit-none` | `limit-default`, `limit-8` |
| Seconds the service was unhealthy | `limit-none-startup-10s` | `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Replica-seconds (cost) | `limit-default` | `static-24`, `limit-16` |
| Replica-seconds (cost) | `limit-8` | `static-24`, `limit-16`, `limit-none` |
| Replica-seconds (cost) | `limit-16` | `static-24` |
| Replica-seconds (cost) | `limit-none` | `static-24` |
| Replica-seconds (cost) | `limit-none-startup-10s` | `static-24`, `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Replica-seconds per good request | `limit-default` | `static-24` |
| Replica-seconds per good request | `limit-8` | `static-24` |
| Replica-seconds per good request | `limit-16` | `static-24` |
| Replica-seconds per good request | `limit-none` | `static-24`, `limit-default` |
| Replica-seconds per good request | `limit-none-startup-10s` | `static-24`, `limit-default`, `limit-8`, `limit-16`, `limit-none` |
