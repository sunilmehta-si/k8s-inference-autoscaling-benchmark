## Is it the control loop? The decision period, with the scale-up limit lifted, and pods that start at once

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `sync-30s` | `sync-30s=hpa-concurrency:up_pods=32,startup=10,sync=30` | 2 | 10 s | 30 s |
| `sync-15s` | `sync-15s=hpa-concurrency:up_pods=32,startup=10,sync=15` | 2 | 10 s | 15 s |
| `sync-5s` | `sync-5s=hpa-concurrency:up_pods=32,startup=10,sync=5` | 2 | 10 s | 5 s |
| `sync-1s` | `sync-1s=hpa-concurrency:up_pods=32,startup=10,sync=1` | 2 | 10 s | 1 s |
| `instant` | `instant=hpa-concurrency:up_pods=32,startup=1,sync=1` | 2 | 1 s | 1 s |

| Metric | `static-24` | `sync-30s` | `sync-15s` | `sync-5s` | `sync-1s` | `instant` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **190 <sub>(185–192)</sub>** | 220 <sub>(216–222)</sub> | 218 <sub>(217–224)</sub> | 218 <sub>(214–221)</sub> | 218 <sub>(214–220)</sub> | 205 <sub>(201–208)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **643 <sub>(623–676)</sub>** | 24,177 <sub>(23,091–25,104)</sub> | 11,444 <sub>(10,447–12,151)</sub> | 5,174 <sub>(4,845–5,924)</sub> | 3,463 <sub>(2,790–3,939)</sub> | 713 <sub>(700–746)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 29,020 <sub>(27,715–30,045)</sub> | 16,104 <sub>(15,235–16,993)</sub> | 9,192 <sub>(9,022–10,098)</sub> | 7,668 <sub>(7,370–8,171)</sub> | 1,171 <sub>(1,148–1,212)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 88.8% <sub>(88.0%–89.8%)</sub> | 90.0% <sub>(89.4%–90.6%)</sub> | 91.2% <sub>(90.8%–92.5%)</sub> | 92.4% <sub>(91.8%–94.2%)</sub> | **100.0% <sub>(100.0%–100.0%)</sub>** |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 110 <sub>(90–140)</sub> | 80 <sub>(70–90)</sub> | 55 <sub>(50–80)</sub> | 50 <sub>(50–70)</sub> | **0** |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | 30,611 <sub>(29,538–31,535)</sub> | 28,742 <sub>(26,929–30,556)</sub> | 28,390 <sub>(27,012–29,719)</sub> | 28,218 <sub>(27,790–29,796)</sub> | **26,933 <sub>(26,215–27,584)</sub>** |
| Replica-seconds per good request <sub>lower is better</sub> | 3.04 <sub>(3.00–3.06)</sub> | 2.42 <sub>(2.30–2.47)</sub> | 2.25 <sub>(2.10–2.40)</sub> | 2.19 <sub>(2.07–2.29)</sub> | 2.15 <sub>(2.10–2.28)</sub> | **1.88 <sub>(1.85–1.94)</sub>** |
| Mean replicas | 24.0 | 17.0 <sub>(16.4–17.5)</sub> | 16.0 <sub>(15.0–17.0)</sub> | 15.8 <sub>(15.0–16.5)</sub> | 15.7 <sub>(15.4–16.6)</sub> | 15.0 <sub>(14.6–15.3)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 | 31 <sub>(28–32)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | **18 <sub>(1–23)</sub>** | 838 <sub>(804–869)</sub> | 758 <sub>(742–778)</sub> | 410 <sub>(397–447)</sub> | 342 <sub>(320–363)</sub> | 42 <sub>(24–49)</sub> |
| Scale-ups | 0 | 5 <sub>(4–6)</sub> | 6 <sub>(5–7)</sub> | 10 <sub>(8–11)</sub> | 19 <sub>(17–20)</sub> | 18 <sub>(17–20)</sub> |
| Scale-downs | 0 | 5 <sub>(4–7)</sub> | 7 <sub>(5–9)</sub> | 10 <sub>(7–12)</sub> | 16 <sub>(14–20)</sub> | 18 <sub>(15–19)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(1–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(1–2)</sub> | 2 <sub>(1–3)</sub> | 2 <sub>(1–3)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s`, `instant` |
| TTFT p95 (ms) | `sync-15s` | `sync-30s` |
| TTFT p95 (ms) | `sync-5s` | `sync-30s`, `sync-15s` |
| TTFT p95 (ms) | `sync-1s` | `sync-30s`, `sync-15s`, `sync-5s` |
| TTFT p95 (ms) | `instant` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Goodput (TTFT within the objective) | `static-24` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Goodput (TTFT within the objective) | `sync-15s` | `sync-30s` |
| Goodput (TTFT within the objective) | `sync-5s` | `sync-30s`, `sync-15s` |
| Goodput (TTFT within the objective) | `sync-1s` | `sync-30s`, `sync-15s`, `sync-5s` |
| Goodput (TTFT within the objective) | `instant` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Seconds the service was unhealthy | `static-24` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Seconds the service was unhealthy | `sync-15s` | `sync-30s` |
| Seconds the service was unhealthy | `sync-5s` | `sync-30s`, `sync-15s` |
| Seconds the service was unhealthy | `sync-1s` | `sync-30s`, `sync-15s` |
| Seconds the service was unhealthy | `instant` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Replica-seconds (cost) | `sync-30s` | `static-24` |
| Replica-seconds (cost) | `sync-15s` | `static-24` |
| Replica-seconds (cost) | `sync-5s` | `static-24` |
| Replica-seconds (cost) | `sync-1s` | `static-24` |
| Replica-seconds (cost) | `instant` | `static-24`, `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Replica-seconds per good request | `sync-30s` | `static-24` |
| Replica-seconds per good request | `sync-15s` | `static-24` |
| Replica-seconds per good request | `sync-5s` | `static-24`, `sync-30s`, `sync-15s` |
| Replica-seconds per good request | `sync-1s` | `static-24`, `sync-30s`, `sync-15s` |
| Replica-seconds per good request | `instant` | `static-24`, `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
