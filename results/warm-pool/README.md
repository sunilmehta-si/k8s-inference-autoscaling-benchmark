## How much standing headroom buys the objective?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `min-2` | `min-2=hpa-concurrency:min=2` | 2 | 45 s | 15 s |
| `min-4` | `min-4=hpa-concurrency:min=4` | 4 | 45 s | 15 s |
| `min-6` | `min-6=hpa-concurrency:min=6` | 6 | 45 s | 15 s |
| `min-8` | `min-8=hpa-concurrency:min=8` | 8 | 45 s | 15 s |
| `min-12` | `min-12=hpa-concurrency:min=12` | 12 | 45 s | 15 s |

| Metric | `static-24` | `min-2` | `min-4` | `min-6` | `min-8` | `min-12` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **190 <sub>(185–192)</sub>** | 243 <sub>(236–252)</sub> | 240 <sub>(232–246)</sub> | 237 <sub>(228–239)</sub> | 231 <sub>(224–246)</sub> | 225 <sub>(217–239)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **643 <sub>(623–676)</sub>** | 47,125 <sub>(40,499–50,987)</sub> | 41,701 <sub>(37,558–44,566)</sub> | 25,679 <sub>(22,237–27,917)</sub> | 17,252 <sub>(14,702–18,934)</sub> | 5,970 <sub>(4,085–7,076)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 61,179 <sub>(57,387–64,283)</sub> | 58,658 <sub>(56,746–59,097)</sub> | 47,467 <sub>(45,297–47,760)</sub> | 37,386 <sub>(35,530–37,811)</sub> | 20,160 <sub>(17,058–21,207)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 80.3% <sub>(79.9%–81.7%)</sub> | 80.5% <sub>(80.0%–81.6%)</sub> | 81.7% <sub>(81.0%–83.1%)</sub> | 84.2% <sub>(81.7%–85.0%)</sub> | 93.5% <sub>(91.2%–93.7%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 215 <sub>(180–240)</sub> | 180 <sub>(180–190)</sub> | 165 <sub>(160–170)</sub> | 145 <sub>(140–170)</sub> | 65 <sub>(60–110)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | **32,053 <sub>(31,702–32,220)</sub>** | 32,315 <sub>(32,132–32,504)</sub> | 33,350 <sub>(33,085–33,837)</sub> | 34,564 <sub>(34,279–35,776)</sub> | 33,076 <sub>(31,445–34,198)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.04 <sub>(3.00–3.06)</sub> | 2.79 <sub>(2.72–2.83)</sub> | 2.82 <sub>(2.75–2.85)</sub> | 2.86 <sub>(2.80–2.93)</sub> | 2.88 <sub>(2.82–3.04)</sub> | **2.49 <sub>(2.36–2.63)</sub>** |
| Mean replicas | 24.0 | 17.8 <sub>(17.6–17.9)</sub> | 18.0 <sub>(17.9–18.1)</sub> | 18.5 <sub>(18.4–18.8)</sub> | 19.2 <sub>(19.0–19.9)</sub> | 18.4 <sub>(17.5–19.0)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **18 <sub>(1–23)</sub>** | 838 <sub>(816–869)</sub> | 813 <sub>(765–844)</sub> | 716 <sub>(666–734)</sub> | 616 <sub>(574–640)</sub> | 434 <sub>(397–456)</sub> |
| Scale-ups | 0 | 10 <sub>(9–12)</sub> | 7 <sub>(6–9)</sub> | 8 <sub>(7–8)</sub> | 6 <sub>(5–6)</sub> | 6 <sub>(4–7)</sub> |
| Scale-downs | 0 | 7 <sub>(6–7)</sub> | 7 <sub>(6–8)</sub> | 7 <sub>(6–8)</sub> | 5 <sub>(5–6)</sub> | 4 <sub>(4–5)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–2)</sub> | 1 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(1–3)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `min-2`, `min-4`, `min-6`, `min-8`, `min-12` |
| TTFT p95 (ms) | `min-6` | `min-2`, `min-4` |
| TTFT p95 (ms) | `min-8` | `min-2`, `min-4`, `min-6` |
| TTFT p95 (ms) | `min-12` | `min-2`, `min-4`, `min-6`, `min-8` |
| Goodput (TTFT within the objective) | `static-24` | `min-2`, `min-4`, `min-6`, `min-8`, `min-12` |
| Goodput (TTFT within the objective) | `min-6` | `min-2`, `min-4` |
| Goodput (TTFT within the objective) | `min-8` | `min-2`, `min-4`, `min-6` |
| Goodput (TTFT within the objective) | `min-12` | `min-2`, `min-4`, `min-6`, `min-8` |
| Seconds the service was unhealthy | `static-24` | `min-2`, `min-4`, `min-6`, `min-8`, `min-12` |
| Seconds the service was unhealthy | `min-6` | `min-2`, `min-4` |
| Seconds the service was unhealthy | `min-8` | `min-2`, `min-4` |
| Seconds the service was unhealthy | `min-12` | `min-2`, `min-4`, `min-6`, `min-8` |
| Replica-seconds (cost) | `min-2` | `static-24`, `min-6`, `min-8` |
| Replica-seconds (cost) | `min-4` | `static-24`, `min-6`, `min-8` |
| Replica-seconds (cost) | `min-6` | `static-24`, `min-8` |
| Replica-seconds (cost) | `min-8` | `static-24` |
| Replica-seconds (cost) | `min-12` | `static-24`, `min-8` |
| Replica-seconds per good request | `min-2` | `static-24`, `min-4`, `min-6`, `min-8` |
| Replica-seconds per good request | `min-4` | `static-24`, `min-6`, `min-8` |
| Replica-seconds per good request | `min-6` | `static-24` |
| Replica-seconds per good request | `min-12` | `static-24`, `min-2`, `min-4`, `min-6`, `min-8` |
