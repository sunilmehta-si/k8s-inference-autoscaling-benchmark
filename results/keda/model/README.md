## Does the autoscaler KEDA creates decide differently? The model, before the cluster

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `hpa-concurrency` | `hpa-concurrency=hpa-concurrency:route=pod,scrape=15` | 2 | 45 s | 15 s |
| `keda-concurrency` | `keda-concurrency=keda-concurrency:route=pod,scrape=15` | 2 | 45 s | 15 s |
| `hpa-queue` | `hpa-queue=hpa-queue:route=pod,scrape=15` | 2 | 45 s | 15 s |
| `keda-queue` | `keda-queue=keda-queue:route=pod,scrape=15` | 2 | 45 s | 15 s |
| `hpa-utilization` | `hpa-utilization=hpa-utilization:route=pod,scrape=15` | 2 | 45 s | 15 s |
| `keda-utilization` | `keda-utilization=keda-utilization:route=pod,scrape=15` | 2 | 45 s | 15 s |

| Metric | `hpa-concurrency` | `keda-concurrency` | `hpa-queue` | `keda-queue` | `hpa-utilization` | `keda-utilization` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **258 <sub>(250–270)</sub>** | **258 <sub>(250–270)</sub>** | 278 <sub>(242–354)</sub> | 273 <sub>(242–354)</sub> | 7,394 <sub>(1,350–18,438)</sub> | 6,344 <sub>(1,350–12,972)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **97,044 <sub>(58,926–113,106)</sub>** | **97,044 <sub>(58,926–113,106)</sub>** | 159,388 <sub>(119,248–239,692)</sub> | 150,760 <sub>(119,248–239,692)</sub> | 148,631 <sub>(101,840–179,010)</sub> | 148,631 <sub>(101,924–179,010)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **136,767 <sub>(111,816–169,292)</sub>** | **136,767 <sub>(111,816–169,292)</sub>** | 290,045 <sub>(254,996–365,739)</sub> | 294,889 <sub>(254,996–365,739)</sub> | 175,120 <sub>(113,189–200,528)</sub> | 175,120 <sub>(113,486–200,528)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **77.3% <sub>(76.4%–78.8%)</sub>** | **77.3% <sub>(76.4%–78.8%)</sub>** | 74.6% <sub>(65.8%–82.6%)</sub> | 75.1% <sub>(65.8%–82.6%)</sub> | 42.5% <sub>(37.5%–51.8%)</sub> | 44.0% <sub>(37.5%–51.8%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **545 <sub>(450–570)</sub>** | **545 <sub>(450–570)</sub>** | **545 <sub>(470–630)</sub>** | **545 <sub>(470–630)</sub>** | 925 <sub>(760–1,090)</sub> | 905 <sub>(790–1,090)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 36,338 <sub>(35,093–36,828)</sub> | 36,338 <sub>(35,093–36,828)</sub> | 39,304 <sub>(34,771–49,186)</sub> | 39,209 <sub>(34,771–49,186)</sub> | **22,945 <sub>(22,105–24,214)</sub>** | 23,296 <sub>(22,105–23,944)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | **3.29 <sub>(3.13–3.32)</sub>** | **3.29 <sub>(3.13–3.32)</sub>** | 3.81 <sub>(2.96–4.55)</sub> | 3.81 <sub>(2.96–4.55)</sub> | 3.79 <sub>(3.20–4.14)</sub> | 3.74 <sub>(3.20–4.14)</sub> |
| Mean replicas | 20.2 <sub>(19.5–20.5)</sub> | 20.2 <sub>(19.5–20.5)</sub> | 21.8 <sub>(19.3–27.3)</sub> | 21.8 <sub>(19.3–27.3)</sub> | 12.7 <sub>(12.3–13.5)</sub> | 12.9 <sub>(12.3–13.3)</sub> |
| Peak replicas | 32 | 32 | 32 | 32 | 26 <sub>(24–27)</sub> | 26 <sub>(24–27)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | **853 <sub>(814–896)</sub>** | **853 <sub>(814–896)</sub>** | 1,094 <sub>(904–1,383)</sub> | 1,070 <sub>(904–1,383)</sub> | 1,360 <sub>(1,025–1,579)</sub> | 1,360 <sub>(1,025–1,579)</sub> |
| Scale-ups | 9 <sub>(8–10)</sub> | 9 <sub>(8–10)</sub> | 12 <sub>(9–16)</sub> | 12 <sub>(9–16)</sub> | 13 <sub>(12–15)</sub> | 13 <sub>(11–15)</sub> |
| Scale-downs | 6 <sub>(5–9)</sub> | 6 <sub>(5–9)</sub> | 3 <sub>(2–4)</sub> | 4 <sub>(3–5)</sub> | 7 <sub>(6–8)</sub> | 8 <sub>(6–9)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 <sub>(0–1)</sub> | 0 <sub>(0–1)</sub> | 8 <sub>(1–10)</sub> | 8 <sub>(1–10)</sub> | 0 <sub>(0–1)</sub> | 0 <sub>(0–1)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `hpa-concurrency` | `hpa-queue`, `keda-queue` |
| TTFT p95 (ms) | `keda-concurrency` | `hpa-queue`, `keda-queue` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-utilization`, `keda-utilization` |
| Goodput (TTFT within the objective) | `keda-concurrency` | `hpa-utilization`, `keda-utilization` |
| Goodput (TTFT within the objective) | `hpa-queue` | `hpa-utilization`, `keda-utilization` |
| Goodput (TTFT within the objective) | `keda-queue` | `hpa-utilization`, `keda-utilization` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-utilization`, `keda-utilization` |
| Seconds the service was unhealthy | `keda-concurrency` | `hpa-utilization`, `keda-utilization` |
| Seconds the service was unhealthy | `hpa-queue` | `hpa-utilization`, `keda-utilization` |
| Seconds the service was unhealthy | `keda-queue` | `hpa-utilization`, `keda-utilization` |
| Replica-seconds (cost) | `hpa-utilization` | `hpa-concurrency`, `keda-concurrency`, `hpa-queue`, `keda-queue` |
| Replica-seconds (cost) | `keda-utilization` | `hpa-concurrency`, `keda-concurrency`, `hpa-queue`, `keda-queue` |
