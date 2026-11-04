## Does a lower target buy the objective?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `target-7.5` | `target-7.5=hpa-concurrency:target=7.5` | 2 | 45 s | 15 s |
| `target-6` | `target-6=hpa-concurrency:target=6` | 2 | 45 s | 15 s |
| `target-4.5` | `target-4.5=hpa-concurrency:target=4.5` | 2 | 45 s | 15 s |
| `target-3` | `target-3=hpa-concurrency:target=3` | 2 | 45 s | 15 s |

| Metric | `static-24` | `target-7.5` | `target-6` | `target-4.5` | `target-3` |
|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **190 <sub>(185–192)</sub>** | 289 <sub>(257–295)</sub> | 243 <sub>(236–252)</sub> | 232 <sub>(223–236)</sub> | 219 <sub>(211–223)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **643 <sub>(623–676)</sub>** | 50,553 <sub>(42,088–52,247)</sub> | 47,125 <sub>(40,499–50,987)</sub> | 39,296 <sub>(26,164–42,565)</sub> | 25,236 <sub>(14,665–32,028)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 64,041 <sub>(58,878–64,564)</sub> | 61,179 <sub>(57,387–64,283)</sub> | 57,439 <sub>(47,759–59,097)</sub> | 47,355 <sub>(36,364–52,529)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 76.4% <sub>(71.2%–79.4%)</sub> | 80.3% <sub>(79.9%–81.7%)</sub> | 82.0% <sub>(81.1%–83.7%)</sub> | 85.8% <sub>(83.6%–87.2%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 280 <sub>(230–330)</sub> | 215 <sub>(180–240)</sub> | 190 <sub>(160–230)</sub> | 160 <sub>(130–180)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | **31,991 <sub>(30,446–32,862)</sub>** | 32,053 <sub>(31,702–32,220)</sub> | 34,076 <sub>(33,642–35,087)</sub> | 38,554 <sub>(38,006–40,420)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.04 <sub>(3.00–3.06)</sub> | 2.92 <sub>(2.71–3.22)</sub> | **2.79 <sub>(2.72–2.83)</sub>** | 2.90 <sub>(2.84–3.01)</sub> | 3.16 <sub>(3.11–3.29)</sub> |
| Mean replicas | 24.0 | 17.8 <sub>(16.9–18.3)</sub> | 17.8 <sub>(17.6–17.9)</sub> | 18.9 <sub>(18.7–19.5)</sub> | 21.4 <sub>(21.1–22.5)</sub> |
| Peak replicas | 24 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **18 <sub>(1–23)</sub>** | 864 <sub>(810–897)</sub> | 838 <sub>(816–869)</sub> | 796 <sub>(731–816)</sub> | 720 <sub>(612–757)</sub> |
| Scale-ups | 0 | 12 <sub>(10–14)</sub> | 10 <sub>(9–12)</sub> | 9 <sub>(8–11)</sub> | 8 <sub>(8–10)</sub> |
| Scale-downs | 0 | 6 <sub>(5–8)</sub> | 7 <sub>(6–7)</sub> | 7 <sub>(5–8)</sub> | 6 <sub>(5–9)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 3 <sub>(1–5)</sub> | 1 <sub>(0–2)</sub> | 0 <sub>(0–1)</sub> | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `target-7.5`, `target-6`, `target-4.5`, `target-3` |
| TTFT p95 (ms) | `target-4.5` | `target-6` |
| TTFT p95 (ms) | `target-3` | `target-7.5`, `target-6`, `target-4.5` |
| Goodput (TTFT within the objective) | `static-24` | `target-7.5`, `target-6`, `target-4.5`, `target-3` |
| Goodput (TTFT within the objective) | `target-6` | `target-7.5` |
| Goodput (TTFT within the objective) | `target-4.5` | `target-7.5`, `target-6` |
| Goodput (TTFT within the objective) | `target-3` | `target-7.5`, `target-6`, `target-4.5` |
| Seconds the service was unhealthy | `static-24` | `target-7.5`, `target-6`, `target-4.5`, `target-3` |
| Seconds the service was unhealthy | `target-6` | `target-7.5` |
| Seconds the service was unhealthy | `target-4.5` | `target-7.5` |
| Seconds the service was unhealthy | `target-3` | `target-7.5`, `target-6`, `target-4.5` |
| Replica-seconds (cost) | `target-7.5` | `static-24`, `target-4.5`, `target-3` |
| Replica-seconds (cost) | `target-6` | `static-24`, `target-4.5`, `target-3` |
| Replica-seconds (cost) | `target-4.5` | `static-24`, `target-3` |
| Replica-seconds (cost) | `target-3` | `static-24` |
| Replica-seconds per good request | `static-24` | `target-3` |
| Replica-seconds per good request | `target-6` | `static-24`, `target-4.5`, `target-3` |
| Replica-seconds per good request | `target-4.5` | `static-24`, `target-3` |
