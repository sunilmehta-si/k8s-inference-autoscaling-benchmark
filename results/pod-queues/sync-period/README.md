## Is it the control loop? The decision period, with the scale-up limit lifted, and pods that start at once

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24=static-24:route=pod` | 2 | 45 s | 15 s |
| `sync-30s` | `sync-30s=hpa-concurrency:up_pods=32,startup=10,sync=30,route=pod` | 2 | 10 s | 30 s |
| `sync-15s` | `sync-15s=hpa-concurrency:up_pods=32,startup=10,sync=15,route=pod` | 2 | 10 s | 15 s |
| `sync-5s` | `sync-5s=hpa-concurrency:up_pods=32,startup=10,sync=5,route=pod` | 2 | 10 s | 5 s |
| `sync-1s` | `sync-1s=hpa-concurrency:up_pods=32,startup=10,sync=1,route=pod` | 2 | 10 s | 1 s |
| `instant` | `instant=hpa-concurrency:up_pods=32,startup=1,sync=1,route=pod` | 2 | 1 s | 1 s |

| Metric | `static-24` | `sync-30s` | `sync-15s` | `sync-5s` | `sync-1s` | `instant` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **203 <sub>(199–205)</sub>** | 223 <sub>(218–230)</sub> | 223 <sub>(217–227)</sub> | 222 <sub>(217–228)</sub> | 219 <sub>(216–222)</sub> | 228 <sub>(222–234)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **934 <sub>(881–968)</sub>** | 52,458 <sub>(42,010–61,983)</sub> | 29,660 <sub>(26,125–40,122)</sub> | 7,103 <sub>(4,806–10,673)</sub> | 4,536 <sub>(3,299–5,366)</sub> | 1,690 <sub>(1,456–2,121)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **2,954 <sub>(2,293–3,715)</sub>** | 130,528 <sub>(108,056–163,928)</sub> | 98,860 <sub>(92,240–140,902)</sub> | 56,146 <sub>(50,674–79,160)</sub> | 44,334 <sub>(41,098–52,645)</sub> | 5,444 <sub>(4,666–7,038)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **98.3% <sub>(97.9%–98.7%)</sub>** | 87.7% <sub>(86.7%–88.4%)</sub> | 89.5% <sub>(88.7%–90.6%)</sub> | 92.2% <sub>(91.2%–92.7%)</sub> | 93.2% <sub>(92.4%–94.0%)</sub> | 95.8% <sub>(94.7%–96.3%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **30 <sub>(20–30)</sub>** | 340 <sub>(310–430)</sub> | 290 <sub>(230–340)</sub> | 240 <sub>(160–280)</sub> | 195 <sub>(130–240)</sub> | 180 <sub>(130–280)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | 33,471 <sub>(32,823–34,226)</sub> | 33,126 <sub>(32,289–33,936)</sub> | 31,274 <sub>(29,156–32,950)</sub> | 31,311 <sub>(30,060–32,555)</sub> | **28,520 <sub>(28,202–29,209)</sub>** |
| Replica-seconds per good request <sub>lower is better</sub> | 3.09 <sub>(3.04–3.10)</sub> | 2.70 <sub>(2.59–2.73)</sub> | 2.60 <sub>(2.52–2.65)</sub> | 2.38 <sub>(2.23–2.52)</sub> | 2.35 <sub>(2.27–2.46)</sub> | **2.09 <sub>(2.07–2.13)</sub>** |
| Mean replicas | 24.0 | 18.6 <sub>(18.2–19.0)</sub> | 18.4 <sub>(17.9–18.9)</sub> | 17.4 <sub>(16.2–18.3)</sub> | 17.4 <sub>(16.7–18.1)</sub> | 15.8 <sub>(15.7–16.2)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **66 <sub>(53–102)</sub>** | 838 <sub>(809–867)</sub> | 754 <sub>(735–780)</sub> | 448 <sub>(432–472)</sub> | 376 <sub>(348–386)</sub> | 74 <sub>(62–85)</sub> |
| Scale-ups | 0 | 4 <sub>(4–8)</sub> | 7 <sub>(4–9)</sub> | 11 <sub>(9–12)</sub> | 20 <sub>(18–24)</sub> | 19 <sub>(17–21)</sub> |
| Scale-downs | 0 | 6 <sub>(5–8)</sub> | 8 <sub>(6–11)</sub> | 14 <sub>(11–18)</sub> | 27 <sub>(24–30)</sub> | 17 <sub>(16–21)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 <sub>(0–2)</sub> | 1 <sub>(0–2)</sub> | 2 <sub>(1–3)</sub> | 1 <sub>(1–3)</sub> | 2 <sub>(1–4)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s`, `instant` |
| TTFT p95 (ms) | `sync-15s` | `sync-30s` |
| TTFT p95 (ms) | `sync-5s` | `sync-30s`, `sync-15s` |
| TTFT p95 (ms) | `sync-1s` | `sync-30s`, `sync-15s`, `sync-5s` |
| TTFT p95 (ms) | `instant` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Goodput (TTFT within the objective) | `static-24` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s`, `instant` |
| Goodput (TTFT within the objective) | `sync-15s` | `sync-30s` |
| Goodput (TTFT within the objective) | `sync-5s` | `sync-30s`, `sync-15s` |
| Goodput (TTFT within the objective) | `sync-1s` | `sync-30s`, `sync-15s`, `sync-5s` |
| Goodput (TTFT within the objective) | `instant` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Seconds the service was unhealthy | `static-24` | `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s`, `instant` |
| Seconds the service was unhealthy | `sync-15s` | `sync-30s` |
| Seconds the service was unhealthy | `sync-5s` | `sync-30s`, `sync-15s` |
| Seconds the service was unhealthy | `sync-1s` | `sync-30s`, `sync-15s` |
| Seconds the service was unhealthy | `instant` | `sync-30s`, `sync-15s` |
| Replica-seconds (cost) | `sync-30s` | `static-24` |
| Replica-seconds (cost) | `sync-15s` | `static-24` |
| Replica-seconds (cost) | `sync-5s` | `static-24`, `sync-30s`, `sync-15s` |
| Replica-seconds (cost) | `sync-1s` | `static-24`, `sync-30s`, `sync-15s` |
| Replica-seconds (cost) | `instant` | `static-24`, `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
| Replica-seconds per good request | `sync-30s` | `static-24` |
| Replica-seconds per good request | `sync-15s` | `static-24`, `sync-30s` |
| Replica-seconds per good request | `sync-5s` | `static-24`, `sync-30s`, `sync-15s` |
| Replica-seconds per good request | `sync-1s` | `static-24`, `sync-30s`, `sync-15s` |
| Replica-seconds per good request | `instant` | `static-24`, `sync-30s`, `sync-15s`, `sync-5s`, `sync-1s` |
