## Is the HPA's scale-up limit the bottleneck?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24=static-24:route=pod` | 2 | 45 s | 15 s |
| `limit-default` | `limit-default=hpa-concurrency:route=pod` | 2 | 45 s | 15 s |
| `limit-8` | `limit-8=hpa-concurrency:up_pods=8,up_percent=200,route=pod` | 2 | 45 s | 15 s |
| `limit-16` | `limit-16=hpa-concurrency:up_pods=16,up_percent=400,route=pod` | 2 | 45 s | 15 s |
| `limit-none` | `limit-none=hpa-concurrency:up_pods=32,route=pod` | 2 | 45 s | 15 s |
| `limit-none-startup-10s` | `limit-none-startup-10s=hpa-concurrency:up_pods=32,startup=10,route=pod` | 2 | 10 s | 15 s |

| Metric | `static-24` | `limit-default` | `limit-8` | `limit-16` | `limit-none` | `limit-none-startup-10s` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **203 <sub>(199–205)</sub>** | 250 <sub>(240–262)</sub> | 249 <sub>(235–258)</sub> | 245 <sub>(235–260)</sub> | 246 <sub>(234–259)</sub> | 223 <sub>(217–227)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **934 <sub>(881–968)</sub>** | 79,368 <sub>(54,084–85,692)</sub> | 74,812 <sub>(52,449–83,284)</sub> | 77,140 <sub>(52,141–82,522)</sub> | 76,836 <sub>(51,925–82,256)</sub> | 29,660 <sub>(26,125–40,122)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **2,954 <sub>(2,293–3,715)</sub>** | 117,707 <sub>(110,475–169,624)</sub> | 115,612 <sub>(110,957–169,439)</sub> | 115,241 <sub>(110,445–168,842)</sub> | 115,241 <sub>(110,356–168,842)</sub> | 98,860 <sub>(92,240–140,902)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **98.3% <sub>(97.9%–98.7%)</sub>** | 80.1% <sub>(78.7%–81.4%)</sub> | 81.1% <sub>(79.8%–82.5%)</sub> | 81.4% <sub>(79.2%–82.6%)</sub> | 81.4% <sub>(79.4%–82.6%)</sub> | 89.5% <sub>(88.7%–90.6%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **30 <sub>(20–30)</sub>** | 480 <sub>(410–530)</sub> | 465 <sub>(440–500)</sub> | 480 <sub>(430–520)</sub> | 485 <sub>(430–520)</sub> | 290 <sub>(230–340)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | 35,475 <sub>(34,442–35,755)</sub> | 35,679 <sub>(34,689–36,061)</sub> | 35,969 <sub>(34,885–36,287)</sub> | 36,143 <sub>(35,085–36,397)</sub> | **33,126 <sub>(32,289–33,936)</sub>** |
| Replica-seconds per good request <sub>lower is better</sub> | 3.09 <sub>(3.04–3.10)</sub> | 3.10 <sub>(3.00–3.18)</sub> | 3.08 <sub>(2.99–3.18)</sub> | 3.09 <sub>(2.99–3.22)</sub> | 3.11 <sub>(3.01–3.23)</sub> | **2.60 <sub>(2.52–2.65)</sub>** |
| Mean replicas | 24.0 | 19.7 <sub>(19.1–19.9)</sub> | 19.8 <sub>(19.3–20.0)</sub> | 20.0 <sub>(19.4–20.2)</sub> | 20.1 <sub>(19.5–20.2)</sub> | 18.4 <sub>(17.9–18.9)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **66 <sub>(53–102)</sub>** | 832 <sub>(811–859)</sub> | 824 <sub>(808–861)</sub> | 834 <sub>(808–870)</sub> | 834 <sub>(808–870)</sub> | 754 <sub>(735–780)</sub> |
| Scale-ups | 0 | 10 <sub>(9–12)</sub> | 8 <sub>(7–10)</sub> | 8 <sub>(7–10)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(4–9)</sub> |
| Scale-downs | 0 | 8 <sub>(6–9)</sub> | 8 <sub>(7–10)</sub> | 8 <sub>(7–10)</sub> | 8 <sub>(7–10)</sub> | 8 <sub>(6–11)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–2)</sub> | 1 <sub>(0–2)</sub> | 0 <sub>(0–2)</sub> | 0 <sub>(0–2)</sub> | 1 <sub>(0–2)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `limit-default`, `limit-8`, `limit-16`, `limit-none`, `limit-none-startup-10s` |
| TTFT p95 (ms) | `limit-8` | `limit-default` |
| TTFT p95 (ms) | `limit-none-startup-10s` | `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Goodput (TTFT within the objective) | `static-24` | `limit-default`, `limit-8`, `limit-16`, `limit-none`, `limit-none-startup-10s` |
| Goodput (TTFT within the objective) | `limit-8` | `limit-default` |
| Goodput (TTFT within the objective) | `limit-16` | `limit-default` |
| Goodput (TTFT within the objective) | `limit-none` | `limit-default` |
| Goodput (TTFT within the objective) | `limit-none-startup-10s` | `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Seconds the service was unhealthy | `static-24` | `limit-default`, `limit-8`, `limit-16`, `limit-none`, `limit-none-startup-10s` |
| Seconds the service was unhealthy | `limit-none-startup-10s` | `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Replica-seconds (cost) | `limit-default` | `static-24`, `limit-16`, `limit-none` |
| Replica-seconds (cost) | `limit-8` | `static-24`, `limit-16`, `limit-none` |
| Replica-seconds (cost) | `limit-16` | `static-24` |
| Replica-seconds (cost) | `limit-none` | `static-24` |
| Replica-seconds (cost) | `limit-none-startup-10s` | `static-24`, `limit-default`, `limit-8`, `limit-16`, `limit-none` |
| Replica-seconds per good request | `limit-none-startup-10s` | `static-24`, `limit-default`, `limit-8`, `limit-16`, `limit-none` |
