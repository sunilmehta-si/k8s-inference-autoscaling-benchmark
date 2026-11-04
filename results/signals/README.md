## Which signal should the autoscaler follow?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-2` | `static-2` | 2 | 45 s | 15 s |
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency` | 2 | 45 s | 15 s |
| `hpa-queue` | `hpa-queue` | 2 | 45 s | 15 s |
| `hpa-rps` | `hpa-rps` | 2 | 45 s | 15 s |

| Metric | `static-2` | `static-24` | `hpa-utilization` | `hpa-concurrency` | `hpa-queue` | `hpa-rps` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | 1,349,029 <sub>(1,280,829–1,375,190)</sub> | **190 <sub>(185–192)</sub>** | 311 <sub>(266–335)</sub> | 243 <sub>(236–252)</sub> | 355 <sub>(306–400)</sub> | 673 <sub>(539–713)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | 2,479,395 <sub>(2,387,954–2,547,759)</sub> | **643 <sub>(623–676)</sub>** | 47,005 <sub>(37,689–48,199)</sub> | 47,125 <sub>(40,499–50,987)</sub> | 55,987 <sub>(47,043–60,558)</sub> | 51,254 <sub>(49,939–53,056)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | 2,593,219 <sub>(2,502,773–2,656,321)</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 75,969 <sub>(58,595–78,085)</sub> | 61,179 <sub>(57,387–64,283)</sub> | 61,751 <sub>(54,293–69,138)</sub> | 65,725 <sub>(63,235–66,146)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | 4.9% <sub>(2.6%–6.0%)</sub> | **100.0%** | 68.7% <sub>(65.8%–75.9%)</sub> | 80.3% <sub>(79.9%–81.7%)</sub> | 63.7% <sub>(61.1%–73.6%)</sub> | 54.0% <sub>(53.1%–58.3%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | 1,630 <sub>(1,560–1,760)</sub> | **0** | 325 <sub>(260–340)</sub> | 215 <sub>(180–240)</sub> | 395 <sub>(330–450)</sub> | 425 <sub>(380–470)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | **3,600** | 43,200 | 27,893 <sub>(27,533–29,613)</sub> | 32,053 <sub>(31,702–32,220)</sub> | 33,521 <sub>(29,952–35,594)</sub> | 18,469 <sub>(17,994–18,771)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 5.12 <sub>(4.24–9.76)</sub> | 3.04 <sub>(3.00–3.06)</sub> | 2.91 <sub>(2.68–2.97)</sub> | 2.79 <sub>(2.72–2.83)</sub> | 3.70 <sub>(2.87–4.04)</sub> | **2.37 <sub>(2.24–2.48)</sub>** |
| Mean replicas | 2.0 | 24.0 | 15.5 <sub>(15.3–16.5)</sub> | 17.8 <sub>(17.6–17.9)</sub> | 18.6 <sub>(16.6–19.8)</sub> | 10.3 <sub>(10.0–10.4)</sub> |
| Peak replicas | 2 | 24 | 32 | 32 | 32 | 15 <sub>(14–16)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | 8,464 <sub>(8,298–8,675)</sub> | **18 <sub>(1–23)</sub>** | 857 <sub>(765–935)</sub> | 838 <sub>(816–869)</sub> | 1,120 <sub>(1,070–1,176)</sub> | 916 <sub>(848–959)</sub> |
| Scale-ups | 0 | 0 | 9 <sub>(9–12)</sub> | 10 <sub>(9–12)</sub> | 14 <sub>(13–15)</sub> | 7 <sub>(6–8)</sub> |
| Scale-downs | 0 | 0 | 6 <sub>(4–7)</sub> | 7 <sub>(6–7)</sub> | 3 <sub>(3–4)</sub> | 4 <sub>(3–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 | 0 <sub>(0–1)</sub> | 1 <sub>(0–2)</sub> | 8 <sub>(5–10)</sub> | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `static-2`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| TTFT p95 (ms) | `hpa-utilization` | `static-2`, `hpa-rps` |
| TTFT p95 (ms) | `hpa-concurrency` | `static-2`, `hpa-rps` |
| TTFT p95 (ms) | `hpa-queue` | `static-2` |
| TTFT p95 (ms) | `hpa-rps` | `static-2` |
| Goodput (TTFT within the objective) | `static-24` | `static-2`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-utilization` | `static-2`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `static-2`, `hpa-utilization`, `hpa-queue`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-queue` | `static-2`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-rps` | `static-2` |
| Seconds the service was unhealthy | `static-24` | `static-2`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-utilization` | `static-2`, `hpa-queue`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-concurrency` | `static-2`, `hpa-utilization`, `hpa-queue`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-queue` | `static-2` |
| Seconds the service was unhealthy | `hpa-rps` | `static-2` |
| Replica-seconds (cost) | `static-2` | `static-24`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| Replica-seconds (cost) | `hpa-utilization` | `static-24`, `hpa-concurrency`, `hpa-queue` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24` |
| Replica-seconds (cost) | `hpa-queue` | `static-24` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue` |
| Replica-seconds per good request | `static-24` | `static-2` |
| Replica-seconds per good request | `hpa-utilization` | `static-2`, `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-2`, `static-24`, `hpa-queue` |
| Replica-seconds per good request | `hpa-queue` | `static-2` |
| Replica-seconds per good request | `hpa-rps` | `static-2`, `static-24`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue` |
