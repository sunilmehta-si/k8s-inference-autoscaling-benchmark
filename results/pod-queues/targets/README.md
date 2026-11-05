## Does a lower target buy the objective?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24=static-24:route=pod` | 2 | 45 s | 15 s |
| `target-7.5` | `target-7.5=hpa-concurrency:target=7.5,route=pod` | 2 | 45 s | 15 s |
| `target-6` | `target-6=hpa-concurrency:target=6,route=pod` | 2 | 45 s | 15 s |
| `target-4.5` | `target-4.5=hpa-concurrency:target=4.5,route=pod` | 2 | 45 s | 15 s |
| `target-3` | `target-3=hpa-concurrency:target=3,route=pod` | 2 | 45 s | 15 s |

| Metric | `static-24` | `target-7.5` | `target-6` | `target-4.5` | `target-3` |
|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **203 <sub>(199–205)</sub>** | 253 <sub>(245–289)</sub> | 250 <sub>(240–262)</sub> | 238 <sub>(235–247)</sub> | 228 <sub>(220–231)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **934 <sub>(881–968)</sub>** | 87,200 <sub>(68,739–115,044)</sub> | 79,368 <sub>(54,084–85,692)</sub> | 53,233 <sub>(40,704–64,602)</sub> | 30,216 <sub>(18,431–41,908)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **2,954 <sub>(2,293–3,715)</sub>** | 156,445 <sub>(90,901–170,126)</sub> | 117,707 <sub>(110,475–169,624)</sub> | 108,843 <sub>(84,645–119,308)</sub> | 63,158 <sub>(43,889–87,827)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **98.3% <sub>(97.9%–98.7%)</sub>** | 79.1% <sub>(73.6%–80.0%)</sub> | 80.1% <sub>(78.7%–81.4%)</sub> | 82.5% <sub>(81.4%–83.8%)</sub> | 85.4% <sub>(84.4%–89.2%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **30 <sub>(20–30)</sub>** | 595 <sub>(480–630)</sub> | 480 <sub>(410–530)</sub> | 370 <sub>(310–400)</sub> | 250 <sub>(220–320)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | **35,295 <sub>(34,279–35,917)</sub>** | 35,475 <sub>(34,442–35,755)</sub> | 36,230 <sub>(35,628–36,870)</sub> | 39,872 <sub>(39,373–41,685)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | **3.09 <sub>(3.04–3.10)</sub>** | 3.13 <sub>(3.04–3.39)</sub> | 3.10 <sub>(3.00–3.18)</sub> | 3.09 <sub>(3.00–3.14)</sub> | 3.28 <sub>(3.17–3.30)</sub> |
| Mean replicas | 24.0 | 19.6 <sub>(19.0–20.0)</sub> | 19.7 <sub>(19.1–19.9)</sub> | 20.1 <sub>(19.8–20.5)</sub> | 22.2 <sub>(21.9–23.2)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **66 <sub>(53–102)</sub>** | 853 <sub>(762–890)</sub> | 832 <sub>(811–859)</sub> | 800 <sub>(772–818)</sub> | 699 <sub>(633–760)</sub> |
| Scale-ups | 0 | 10 <sub>(9–13)</sub> | 10 <sub>(9–12)</sub> | 9 <sub>(7–12)</sub> | 9 <sub>(8–11)</sub> |
| Scale-downs | 0 | 8 <sub>(8–10)</sub> | 8 <sub>(6–9)</sub> | 7 <sub>(5–9)</sub> | 5 <sub>(3–7)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 <sub>(0–4)</sub> | 1 <sub>(0–2)</sub> | 0 <sub>(0–1)</sub> | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `target-7.5`, `target-6`, `target-4.5`, `target-3` |
| TTFT p95 (ms) | `target-6` | `target-7.5` |
| TTFT p95 (ms) | `target-4.5` | `target-7.5`, `target-6` |
| TTFT p95 (ms) | `target-3` | `target-7.5`, `target-6`, `target-4.5` |
| Goodput (TTFT within the objective) | `static-24` | `target-7.5`, `target-6`, `target-4.5`, `target-3` |
| Goodput (TTFT within the objective) | `target-4.5` | `target-7.5`, `target-6` |
| Goodput (TTFT within the objective) | `target-3` | `target-7.5`, `target-6`, `target-4.5` |
| Seconds the service was unhealthy | `static-24` | `target-7.5`, `target-6`, `target-4.5`, `target-3` |
| Seconds the service was unhealthy | `target-4.5` | `target-7.5`, `target-6` |
| Seconds the service was unhealthy | `target-3` | `target-7.5`, `target-6`, `target-4.5` |
| Replica-seconds (cost) | `target-7.5` | `static-24`, `target-4.5`, `target-3` |
| Replica-seconds (cost) | `target-6` | `static-24`, `target-4.5`, `target-3` |
| Replica-seconds (cost) | `target-4.5` | `static-24`, `target-3` |
| Replica-seconds (cost) | `target-3` | `static-24` |
| Replica-seconds per good request | `static-24` | `target-3` |
| Replica-seconds per good request | `target-6` | `target-3` |
| Replica-seconds per good request | `target-4.5` | `target-3` |
