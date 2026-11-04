## How much of the miss is pod startup?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `startup-10s` | `startup-10s=hpa-concurrency:startup=10` | 2 | 10 s | 15 s |
| `startup-20s` | `startup-20s=hpa-concurrency:startup=20` | 2 | 20 s | 15 s |
| `startup-45s` | `startup-45s=hpa-concurrency:startup=45` | 2 | 45 s | 15 s |
| `startup-120s` | `startup-120s=hpa-concurrency:startup=120` | 2 | 120 s | 15 s |

| Metric | `static-24` | `startup-10s` | `startup-20s` | `startup-45s` | `startup-120s` |
|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **190 <sub>(185–192)</sub>** | 222 <sub>(216–224)</sub> | 226 <sub>(220–230)</sub> | 243 <sub>(236–252)</sub> | 349 <sub>(318–388)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **643 <sub>(623–676)</sub>** | 25,299 <sub>(22,634–28,717)</sub> | 31,505 <sub>(28,216–35,324)</sub> | 47,125 <sub>(40,499–50,987)</sub> | 77,680 <sub>(60,964–82,623)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 32,110 <sub>(29,687–34,066)</sub> | 40,553 <sub>(38,118–42,594)</sub> | 61,179 <sub>(57,387–64,283)</sub> | 120,683 <sub>(107,159–125,948)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 87.7% <sub>(86.8%–89.9%)</sub> | 85.8% <sub>(85.0%–86.5%)</sub> | 80.3% <sub>(79.9%–81.7%)</sub> | 64.5% <sub>(63.0%–66.6%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 115 <sub>(100–130)</sub> | 145 <sub>(130–160)</sub> | 215 <sub>(180–240)</sub> | 420 <sub>(380–470)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | **29,551 <sub>(27,797–31,330)</sub>** | 30,835 <sub>(30,498–31,675)</sub> | 32,053 <sub>(31,702–32,220)</sub> | 34,901 <sub>(34,677–35,384)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.04 <sub>(3.00–3.06)</sub> | **2.36 <sub>(2.19–2.53)</sub>** | 2.52 <sub>(2.46–2.62)</sub> | 2.79 <sub>(2.72–2.83)</sub> | 3.80 <sub>(3.70–3.89)</sub> |
| Mean replicas | 24.0 | 16.4 <sub>(15.4–17.4)</sub> | 17.1 <sub>(16.9–17.6)</sub> | 17.8 <sub>(17.6–17.9)</sub> | 19.4 <sub>(19.3–19.7)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **18 <sub>(1–23)</sub>** | 785 <sub>(750–815)</sub> | 838 <sub>(804–869)</sub> | 838 <sub>(816–869)</sub> | 1,424 <sub>(1,077–1,656)</sub> |
| Scale-ups | 0 | 10 <sub>(9–10)</sub> | 10 <sub>(9–11)</sub> | 10 <sub>(9–12)</sub> | 10 <sub>(9–11)</sub> |
| Scale-downs | 0 | 8 <sub>(7–9)</sub> | 7 <sub>(5–9)</sub> | 7 <sub>(6–7)</sub> | 6 <sub>(5–7)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–1)</sub> | 1 | 1 <sub>(0–2)</sub> | 0 <sub>(0–2)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `startup-10s`, `startup-20s`, `startup-45s`, `startup-120s` |
| TTFT p95 (ms) | `startup-10s` | `startup-20s`, `startup-45s`, `startup-120s` |
| TTFT p95 (ms) | `startup-20s` | `startup-45s`, `startup-120s` |
| TTFT p95 (ms) | `startup-45s` | `startup-120s` |
| Goodput (TTFT within the objective) | `static-24` | `startup-10s`, `startup-20s`, `startup-45s`, `startup-120s` |
| Goodput (TTFT within the objective) | `startup-10s` | `startup-20s`, `startup-45s`, `startup-120s` |
| Goodput (TTFT within the objective) | `startup-20s` | `startup-45s`, `startup-120s` |
| Goodput (TTFT within the objective) | `startup-45s` | `startup-120s` |
| Seconds the service was unhealthy | `static-24` | `startup-10s`, `startup-20s`, `startup-45s`, `startup-120s` |
| Seconds the service was unhealthy | `startup-10s` | `startup-20s`, `startup-45s`, `startup-120s` |
| Seconds the service was unhealthy | `startup-20s` | `startup-45s`, `startup-120s` |
| Seconds the service was unhealthy | `startup-45s` | `startup-120s` |
| Replica-seconds (cost) | `startup-10s` | `static-24`, `startup-20s`, `startup-45s`, `startup-120s` |
| Replica-seconds (cost) | `startup-20s` | `static-24`, `startup-45s`, `startup-120s` |
| Replica-seconds (cost) | `startup-45s` | `static-24`, `startup-120s` |
| Replica-seconds (cost) | `startup-120s` | `static-24` |
| Replica-seconds per good request | `static-24` | `startup-120s` |
| Replica-seconds per good request | `startup-10s` | `static-24`, `startup-20s`, `startup-45s`, `startup-120s` |
| Replica-seconds per good request | `startup-20s` | `static-24`, `startup-45s`, `startup-120s` |
| Replica-seconds per good request | `startup-45s` | `static-24`, `startup-120s` |
