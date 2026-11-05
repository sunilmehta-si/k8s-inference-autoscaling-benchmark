## Which signal should the autoscaler follow?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-2` | `static-2=static-2:route=pod` | 2 | 45 s | 15 s |
| `static-24` | `static-24=static-24:route=pod` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization=hpa-utilization:route=pod` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency=hpa-concurrency:route=pod` | 2 | 45 s | 15 s |
| `hpa-queue` | `hpa-queue=hpa-queue:route=pod` | 2 | 45 s | 15 s |
| `hpa-rps` | `hpa-rps=hpa-rps:route=pod` | 2 | 45 s | 15 s |

| Metric | `static-2` | `static-24` | `hpa-utilization` | `hpa-concurrency` | `hpa-queue` | `hpa-rps` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | 1,343,694 <sub>(1,295,085–1,366,871)</sub> | **203 <sub>(199–205)</sub>** | 1,323 <sub>(586–3,127)</sub> | 250 <sub>(240–262)</sub> | 258 <sub>(239–267)</sub> | 715 <sub>(603–969)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | 2,479,183 <sub>(2,388,037–2,545,561)</sub> | **934 <sub>(881–968)</sub>** | 114,792 <sub>(71,830–136,357)</sub> | 79,368 <sub>(54,084–85,692)</sub> | 110,278 <sub>(20,704–237,269)</sub> | 160,753 <sub>(143,668–164,721)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | 2,600,956 <sub>(2,543,932–2,706,874)</sub> | **2,954 <sub>(2,293–3,715)</sub>** | 137,379 <sub>(105,555–169,207)</sub> | 117,707 <sub>(110,475–169,624)</sub> | 211,626 <sub>(54,198–282,984)</sub> | 181,653 <sub>(169,659–191,243)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | 3.3% <sub>(2.3%–4.2%)</sub> | **98.3% <sub>(97.9%–98.7%)</sub>** | 51.5% <sub>(48.0%–57.1%)</sub> | 80.1% <sub>(78.7%–81.4%)</sub> | 79.3% <sub>(75.1%–82.8%)</sub> | 60.3% <sub>(57.1%–62.3%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | 1,755 <sub>(1,740–1,770)</sub> | **30 <sub>(20–30)</sub>** | 845 <sub>(690–930)</sub> | 480 <sub>(410–530)</sub> | 515 <sub>(460–690)</sub> | 1,010 <sub>(940–1,110)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | **3,600** | 43,200 | 23,462 <sub>(22,308–24,380)</sub> | 35,475 <sub>(34,442–35,755)</sub> | 37,844 <sub>(35,502–48,057)</sub> | 18,451 <sub>(17,975–18,772)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 7.55 <sub>(6.05–11.15)</sub> | 3.09 <sub>(3.04–3.10)</sub> | 3.16 <sub>(2.84–3.39)</sub> | 3.10 <sub>(3.00–3.18)</sub> | 3.31 <sub>(3.07–4.33)</sub> | **2.14 <sub>(2.08–2.23)</sub>** |
| Mean replicas | 2.0 | 24.0 | 13.0 <sub>(12.4–13.5)</sub> | 19.7 <sub>(19.1–19.9)</sub> | 21.0 <sub>(19.7–26.7)</sub> | 10.3 <sub>(10.0–10.4)</sub> |
| Peak replicas | 2 | 24 | 26 <sub>(23–28)</sub> | 32 | 32 | 15 <sub>(14–16)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | 8,468 <sub>(8,308–8,678)</sub> | **66 <sub>(53–102)</sub>** | 1,086 <sub>(770–1,130)</sub> | 832 <sub>(811–859)</sub> | 918 <sub>(680–1,045)</sub> | 946 <sub>(894–1,009)</sub> |
| Scale-ups | 0 | 0 | 11 <sub>(9–14)</sub> | 10 <sub>(9–12)</sub> | 12 <sub>(11–15)</sub> | 7 <sub>(6–8)</sub> |
| Scale-downs | 0 | 0 | 6 <sub>(5–8)</sub> | 8 <sub>(6–9)</sub> | 4 <sub>(3–5)</sub> | 4 <sub>(3–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 | 0 | 1 <sub>(0–2)</sub> | 8 <sub>(6–10)</sub> | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `static-2`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| TTFT p95 (ms) | `hpa-utilization` | `static-2`, `hpa-rps` |
| TTFT p95 (ms) | `hpa-concurrency` | `static-2`, `hpa-rps` |
| TTFT p95 (ms) | `hpa-queue` | `static-2` |
| TTFT p95 (ms) | `hpa-rps` | `static-2` |
| Goodput (TTFT within the objective) | `static-24` | `static-2`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-utilization` | `static-2` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `static-2`, `hpa-utilization`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-queue` | `static-2`, `hpa-utilization`, `hpa-rps` |
| Goodput (TTFT within the objective) | `hpa-rps` | `static-2`, `hpa-utilization` |
| Seconds the service was unhealthy | `static-24` | `static-2`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-utilization` | `static-2`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-concurrency` | `static-2`, `hpa-utilization`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-queue` | `static-2`, `hpa-utilization`, `hpa-rps` |
| Seconds the service was unhealthy | `hpa-rps` | `static-2` |
| Replica-seconds (cost) | `static-2` | `static-24`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue`, `hpa-rps` |
| Replica-seconds (cost) | `hpa-utilization` | `static-24`, `hpa-concurrency`, `hpa-queue` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue` |
| Replica-seconds per good request | `static-24` | `static-2`, `hpa-queue` |
| Replica-seconds per good request | `hpa-utilization` | `static-2` |
| Replica-seconds per good request | `hpa-concurrency` | `static-2`, `hpa-queue` |
| Replica-seconds per good request | `hpa-queue` | `static-2` |
| Replica-seconds per good request | `hpa-rps` | `static-2`, `static-24`, `hpa-utilization`, `hpa-concurrency`, `hpa-queue` |
