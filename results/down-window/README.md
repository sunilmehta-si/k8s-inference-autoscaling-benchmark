## What does a shorter scale-down window cost, and what does it save?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `conc-down-300` | `conc-down-300=hpa-concurrency:down=300` | 2 | 45 s | 15 s |
| `conc-down-120` | `conc-down-120=hpa-concurrency:down=120` | 2 | 45 s | 15 s |
| `conc-down-60` | `conc-down-60=hpa-concurrency:down=60` | 2 | 45 s | 15 s |
| `conc-down-30` | `conc-down-30=hpa-concurrency:down=30` | 2 | 45 s | 15 s |
| `queue-down-300` | `queue-down-300=hpa-queue:down=300` | 2 | 45 s | 15 s |
| `queue-down-60` | `queue-down-60=hpa-queue:down=60` | 2 | 45 s | 15 s |

| Metric | `conc-down-300` | `conc-down-120` | `conc-down-60` | `conc-down-30` | `queue-down-300` | `queue-down-60` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **243 <sub>(236–252)</sub>** | 335 <sub>(311–344)</sub> | 358 <sub>(322–377)</sub> | 414 <sub>(374–458)</sub> | 355 <sub>(306–400)</sub> | 9,268 <sub>(5,009–12,073)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **47,125 <sub>(40,499–50,987)</sub>** | **47,125 <sub>(40,499–50,987)</sub>** | 50,857 <sub>(43,879–59,754)</sub> | 51,587 <sub>(41,095–60,548)</sub> | 55,987 <sub>(47,043–60,558)</sub> | 56,590 <sub>(51,400–60,732)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **61,179 <sub>(57,387–64,283)</sub>** | **61,179 <sub>(57,387–64,283)</sub>** | 64,162 <sub>(59,526–67,615)</sub> | 64,196 <sub>(49,563–69,133)</sub> | 61,751 <sub>(54,293–69,138)</sub> | 62,005 <sub>(53,065–69,138)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **80.3% <sub>(79.9%–81.7%)</sub>** | 66.5% <sub>(64.8%–68.6%)</sub> | 66.4% <sub>(64.6%–70.0%)</sub> | 64.1% <sub>(63.5%–68.4%)</sub> | 63.7% <sub>(61.1%–73.6%)</sub> | 42.5% <sub>(40.3%–43.9%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **215 <sub>(180–240)</sub>** | 350 <sub>(300–380)</sub> | 350 <sub>(320–400)</sub> | 430 <sub>(380–530)</sub> | 395 <sub>(330–450)</sub> | 760 <sub>(680–840)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 32,053 <sub>(31,702–32,220)</sub> | 25,722 <sub>(25,278–26,362)</sub> | 21,321 <sub>(21,033–21,602)</sub> | **18,817 <sub>(18,656–19,335)</sub>** | 33,521 <sub>(29,952–35,594)</sub> | 24,429 <sub>(24,258–25,583)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.79 <sub>(2.72–2.83)</sub> | 2.71 <sub>(2.61–2.82)</sub> | 2.26 <sub>(2.13–2.31)</sub> | **2.06 <sub>(1.92–2.14)</sub>** | 3.70 <sub>(2.87–4.04)</sub> | 4.11 <sub>(3.90–4.40)</sub> |
| Mean replicas | 17.8 <sub>(17.6–17.9)</sub> | 14.3 <sub>(14.0–14.6)</sub> | 11.8 <sub>(11.7–12.0)</sub> | 10.5 <sub>(10.4–10.7)</sub> | 18.6 <sub>(16.6–19.8)</sub> | 13.6 <sub>(13.5–14.2)</sub> |
| Peak replicas | 32 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **838 <sub>(816–869)</sub>** | 852 <sub>(816–875)</sub> | 872 <sub>(816–937)</sub> | 907 <sub>(816–939)</sub> | 1,120 <sub>(1,070–1,176)</sub> | 1,120 <sub>(1,085–1,158)</sub> |
| Scale-ups | 10 <sub>(9–12)</sub> | 14 <sub>(13–17)</sub> | 18 <sub>(16–20)</sub> | 22 <sub>(18–25)</sub> | 14 <sub>(13–15)</sub> | 28 <sub>(27–30)</sub> |
| Scale-downs | 7 <sub>(6–7)</sub> | 9 <sub>(7–12)</sub> | 14 <sub>(12–16)</sub> | 18 <sub>(14–24)</sub> | 3 <sub>(3–4)</sub> | 10 <sub>(8–11)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 1 <sub>(0–2)</sub> | 6 <sub>(4–11)</sub> | 8 <sub>(3–10)</sub> | 16 <sub>(9–21)</sub> | 8 <sub>(5–10)</sub> | 21 <sub>(16–28)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `conc-down-300` | `queue-down-60` |
| TTFT p95 (ms) | `conc-down-120` | `queue-down-60` |
| TTFT p95 (ms) | `conc-down-60` | `queue-down-60` |
| Goodput (TTFT within the objective) | `conc-down-300` | `conc-down-120`, `conc-down-60`, `conc-down-30`, `queue-down-300`, `queue-down-60` |
| Goodput (TTFT within the objective) | `conc-down-120` | `queue-down-60` |
| Goodput (TTFT within the objective) | `conc-down-60` | `conc-down-30`, `queue-down-60` |
| Goodput (TTFT within the objective) | `conc-down-30` | `queue-down-60` |
| Goodput (TTFT within the objective) | `queue-down-300` | `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-300` | `conc-down-120`, `conc-down-60`, `conc-down-30`, `queue-down-300`, `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-120` | `conc-down-30`, `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-60` | `conc-down-30`, `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-30` | `queue-down-60` |
| Seconds the service was unhealthy | `queue-down-300` | `queue-down-60` |
| Replica-seconds (cost) | `conc-down-120` | `conc-down-300`, `queue-down-300` |
| Replica-seconds (cost) | `conc-down-60` | `conc-down-300`, `conc-down-120`, `queue-down-300`, `queue-down-60` |
| Replica-seconds (cost) | `conc-down-30` | `conc-down-300`, `conc-down-120`, `conc-down-60`, `queue-down-300`, `queue-down-60` |
| Replica-seconds (cost) | `queue-down-60` | `conc-down-300`, `conc-down-120`, `queue-down-300` |
| Replica-seconds per good request | `conc-down-300` | `queue-down-300`, `queue-down-60` |
| Replica-seconds per good request | `conc-down-120` | `queue-down-300`, `queue-down-60` |
| Replica-seconds per good request | `conc-down-60` | `conc-down-300`, `conc-down-120`, `queue-down-300`, `queue-down-60` |
| Replica-seconds per good request | `conc-down-30` | `conc-down-300`, `conc-down-120`, `queue-down-300`, `queue-down-60` |
