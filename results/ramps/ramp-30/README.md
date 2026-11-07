## A ramp from 3 to 20 requests per second over 30 s

Workload [ramp-30](../../workloads/ramp-30.json): 16 minutes, about 8,383 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization` | 2 | 45 s | 15 s |
| `cluster-like` | `cluster-like=hpa-concurrency:route=pod,lag=30` | 2 | 45 s | 15 s |

| Metric | `static-24` | `hpa-concurrency` | `hpa-utilization` | `cluster-like` |
|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **189 <sub>(184–191)</sub>** | 240 <sub>(231–249)</sub> | 459 <sub>(284–534)</sub> | 304 <sub>(292–327)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **642 <sub>(621–662)</sub>** | 26,107 <sub>(21,587–31,511)</sub> | 44,494 <sub>(18,686–45,340)</sub> | 95,797 <sub>(57,268–133,631)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,050 <sub>(1,020–1,084)</sub>** | 27,955 <sub>(23,249–32,912)</sub> | 45,230 <sub>(20,047–46,365)</sub> | 115,797 <sub>(69,265–151,436)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 79.5% <sub>(78.1%–80.5%)</sub> | 57.4% <sub>(55.8%–72.9%)</sub> | 70.7% <sub>(68.0%–71.7%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 130 <sub>(110–150)</sub> | 210 <sub>(140–230)</sub> | 385 <sub>(340–430)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 22,320 | **16,568 <sub>(16,425–16,998)</sub>** | 16,710 <sub>(16,395–17,430)</sub> | 19,448 <sub>(18,660–19,590)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.66 <sub>(2.62–2.76)</sub> | **2.50 <sub>(2.46–2.56)</sub>** | 3.47 <sub>(2.85–3.56)</sub> | 3.31 <sub>(3.15–3.44)</sub> |
| Mean replicas | 24.0 | 17.8 <sub>(17.7–18.3)</sub> | 18.0 <sub>(17.6–18.7)</sub> | 20.9 <sub>(20.1–21.1)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 597 <sub>(508–668)</sub> | 901 <sub>(427–986)</sub> | 946 <sub>(733–1,022)</sub> |
| Scale-ups | 0 | 6 <sub>(5–7)</sub> | 6 <sub>(5–8)</sub> | 6 <sub>(4–6)</sub> |
| Scale-downs | 0 | 4 <sub>(2–5)</sub> | 3 <sub>(2–5)</sub> | 2 <sub>(0–3)</sub> |
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
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `cluster-like` |
| Replica-seconds (cost) | `hpa-utilization` | `static-24`, `cluster-like` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds per good request | `static-24` | `hpa-utilization`, `cluster-like` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `hpa-utilization`, `cluster-like` |
