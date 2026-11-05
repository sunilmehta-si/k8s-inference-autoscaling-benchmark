## How much standing headroom buys the objective?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24=static-24:route=pod` | 2 | 45 s | 15 s |
| `min-2` | `min-2=hpa-concurrency:min=2,route=pod` | 2 | 45 s | 15 s |
| `min-4` | `min-4=hpa-concurrency:min=4,route=pod` | 4 | 45 s | 15 s |
| `min-6` | `min-6=hpa-concurrency:min=6,route=pod` | 6 | 45 s | 15 s |
| `min-8` | `min-8=hpa-concurrency:min=8,route=pod` | 8 | 45 s | 15 s |
| `min-12` | `min-12=hpa-concurrency:min=12,route=pod` | 12 | 45 s | 15 s |

| Metric | `static-24` | `min-2` | `min-4` | `min-6` | `min-8` | `min-12` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **203 <sub>(199–205)</sub>** | 250 <sub>(240–262)</sub> | 248 <sub>(243–254)</sub> | 256 <sub>(248–263)</sub> | 250 <sub>(243–256)</sub> | 244 <sub>(238–246)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **934 <sub>(881–968)</sub>** | 79,368 <sub>(54,084–85,692)</sub> | 81,169 <sub>(74,655–89,622)</sub> | 45,733 <sub>(39,726–51,548)</sub> | 26,787 <sub>(23,113–28,445)</sub> | 8,743 <sub>(7,809–9,521)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **2,954 <sub>(2,293–3,715)</sub>** | 117,707 <sub>(110,475–169,624)</sub> | 114,713 <sub>(104,937–118,459)</sub> | 67,321 <sub>(60,368–70,988)</sub> | 44,029 <sub>(38,554–45,776)</sub> | 20,943 <sub>(19,568–21,668)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **98.3% <sub>(97.9%–98.7%)</sub>** | 80.1% <sub>(78.7%–81.4%)</sub> | 80.7% <sub>(79.2%–81.5%)</sub> | 80.0% <sub>(78.6%–81.7%)</sub> | 81.8% <sub>(80.6%–82.7%)</sub> | 86.3% <sub>(84.5%–87.4%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **30 <sub>(20–30)</sub>** | 480 <sub>(410–530)</sub> | 415 <sub>(380–480)</sub> | 355 <sub>(340–380)</sub> | 300 <sub>(270–310)</sub> | 240 <sub>(210–280)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | 35,475 <sub>(34,442–35,755)</sub> | 35,485 <sub>(35,461–36,361)</sub> | **35,446 <sub>(35,076–36,263)</sub>** | 35,783 <sub>(35,340–36,674)</sub> | 36,859 <sub>(35,870–38,811)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.09 <sub>(3.04–3.10)</sub> | 3.10 <sub>(3.00–3.18)</sub> | 3.10 <sub>(3.04–3.19)</sub> | 3.09 <sub>(3.04–3.24)</sub> | 3.05 <sub>(3.02–3.17)</sub> | **2.99 <sub>(2.91–3.22)</sub>** |
| Mean replicas | 24.0 | 19.7 <sub>(19.1–19.9)</sub> | 19.7 <sub>(19.7–20.2)</sub> | 19.7 <sub>(19.5–20.1)</sub> | 19.9 <sub>(19.6–20.4)</sub> | 20.5 <sub>(19.9–21.6)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **66 <sub>(53–102)</sub>** | 832 <sub>(811–859)</sub> | 814 <sub>(769–849)</sub> | 716 <sub>(671–737)</sub> | 620 <sub>(578–638)</sub> | 441 <sub>(404–454)</sub> |
| Scale-ups | 0 | 10 <sub>(9–12)</sub> | 7 <sub>(6–7)</sub> | 8 <sub>(7–9)</sub> | 6 <sub>(4–6)</sub> | 7 <sub>(6–8)</sub> |
| Scale-downs | 0 | 8 <sub>(6–9)</sub> | 8 <sub>(6–8)</sub> | 8 <sub>(6–9)</sub> | 7 <sub>(6–8)</sub> | 5 <sub>(4–7)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–2)</sub> | 1 <sub>(0–1)</sub> | 2 <sub>(1–2)</sub> | 1 <sub>(0–2)</sub> | 2 <sub>(1–3)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `min-2`, `min-4`, `min-6`, `min-8`, `min-12` |
| TTFT p95 (ms) | `min-6` | `min-2`, `min-4` |
| TTFT p95 (ms) | `min-8` | `min-2`, `min-4`, `min-6` |
| TTFT p95 (ms) | `min-12` | `min-2`, `min-4`, `min-6`, `min-8` |
| Goodput (TTFT within the objective) | `static-24` | `min-2`, `min-4`, `min-6`, `min-8`, `min-12` |
| Goodput (TTFT within the objective) | `min-8` | `min-2`, `min-6` |
| Goodput (TTFT within the objective) | `min-12` | `min-2`, `min-4`, `min-6`, `min-8` |
| Seconds the service was unhealthy | `static-24` | `min-2`, `min-4`, `min-6`, `min-8`, `min-12` |
| Seconds the service was unhealthy | `min-4` | `min-2` |
| Seconds the service was unhealthy | `min-6` | `min-2`, `min-4` |
| Seconds the service was unhealthy | `min-8` | `min-2`, `min-4`, `min-6` |
| Seconds the service was unhealthy | `min-12` | `min-2`, `min-4`, `min-6`, `min-8` |
| Replica-seconds (cost) | `min-2` | `static-24`, `min-8`, `min-12` |
| Replica-seconds (cost) | `min-4` | `static-24`, `min-12` |
| Replica-seconds (cost) | `min-6` | `static-24`, `min-12` |
| Replica-seconds (cost) | `min-8` | `static-24` |
| Replica-seconds (cost) | `min-12` | `static-24` |
