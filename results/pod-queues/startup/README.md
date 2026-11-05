## How much of the miss is pod startup?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24=static-24:route=pod` | 2 | 45 s | 15 s |
| `startup-10s` | `startup-10s=hpa-concurrency:startup=10,route=pod` | 2 | 10 s | 15 s |
| `startup-20s` | `startup-20s=hpa-concurrency:startup=20,route=pod` | 2 | 20 s | 15 s |
| `startup-45s` | `startup-45s=hpa-concurrency:startup=45,route=pod` | 2 | 45 s | 15 s |
| `startup-120s` | `startup-120s=hpa-concurrency:startup=120,route=pod` | 2 | 120 s | 15 s |

| Metric | `static-24` | `startup-10s` | `startup-20s` | `startup-45s` | `startup-120s` |
|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **203 <sub>(199–205)</sub>** | 227 <sub>(222–230)</sub> | 234 <sub>(222–239)</sub> | 250 <sub>(240–262)</sub> | 324 <sub>(310–332)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **934 <sub>(881–968)</sub>** | 35,359 <sub>(31,211–50,071)</sub> | 51,443 <sub>(45,025–61,472)</sub> | 79,368 <sub>(54,084–85,692)</sub> | 117,251 <sub>(72,667–163,017)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **2,954 <sub>(2,293–3,715)</sub>** | 104,617 <sub>(97,727–150,081)</sub> | 111,753 <sub>(109,073–163,367)</sub> | 117,707 <sub>(110,475–169,624)</sub> | 163,092 <sub>(113,345–180,889)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **98.3% <sub>(97.9%–98.7%)</sub>** | 87.9% <sub>(87.1%–88.9%)</sub> | 85.2% <sub>(84.1%–87.6%)</sub> | 80.1% <sub>(78.7%–81.4%)</sub> | 67.3% <sub>(66.7%–68.4%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **30 <sub>(20–30)</sub>** | 310 <sub>(270–340)</sub> | 375 <sub>(310–430)</sub> | 480 <sub>(410–530)</sub> | 710 <sub>(610–810)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | **32,439 <sub>(32,175–33,279)</sub>** | 33,705 <sub>(32,930–34,137)</sub> | 35,475 <sub>(34,442–35,755)</sub> | 38,792 <sub>(37,363–40,856)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.09 <sub>(3.04–3.10)</sub> | **2.61 <sub>(2.53–2.67)</sub>** | 2.76 <sub>(2.65–2.85)</sub> | 3.10 <sub>(3.00–3.18)</sub> | 4.05 <sub>(3.86–4.25)</sub> |
| Mean replicas | 24.0 | 18.0 <sub>(17.9–18.5)</sub> | 18.7 <sub>(18.3–19.0)</sub> | 19.7 <sub>(19.1–19.9)</sub> | 21.6 <sub>(20.8–22.7)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **66 <sub>(53–102)</sub>** | 778 <sub>(733–813)</sub> | 824 <sub>(801–856)</sub> | 832 <sub>(811–859)</sub> | 1,176 <sub>(810–1,506)</sub> |
| Scale-ups | 0 | 10 <sub>(8–11)</sub> | 10 <sub>(9–12)</sub> | 10 <sub>(9–12)</sub> | 10 <sub>(9–11)</sub> |
| Scale-downs | 0 | 8 <sub>(7–10)</sub> | 8 <sub>(8–10)</sub> | 8 <sub>(6–9)</sub> | 6 <sub>(5–7)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–2)</sub> | 1 <sub>(0–3)</sub> | 1 <sub>(0–2)</sub> | 0 <sub>(0–1)</sub> |

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
| Replica-seconds per good request | `startup-45s` | `startup-120s` |
