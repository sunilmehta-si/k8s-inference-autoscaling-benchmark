## Does scaling ahead of the load beat reacting to it? (ramp-120)

Workload [ramp-120](../../workloads/ramp-120.json): 17 minutes, about 9,429 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `static-24` | `static-24` | 2 | 45 s | 15 s |
| `hpa-concurrency` | `hpa-concurrency` | 2 | 45 s | 15 s |
| `predict-concurrency` | `predict-concurrency` | 2 | 45 s | 15 s |
| `hpa-rps` | `hpa-rps` | 2 | 45 s | 15 s |
| `predict-rps` | `predict-rps` | 2 | 45 s | 15 s |
| `warm-12` | `warm-12=hpa-concurrency:min=12` | 12 | 45 s | 15 s |
| `cluster-like` | `cluster-like=hpa-concurrency:route=pod,scrape=15` | 2 | 45 s | 15 s |
| `predict-cluster-like` | `predict-cluster-like=predict-concurrency:route=pod,scrape=15` | 2 | 45 s | 15 s |

| Metric | `static-24` | `hpa-concurrency` | `predict-concurrency` | `hpa-rps` | `predict-rps` | `warm-12` | `cluster-like` | `predict-cluster-like` |
|---|---|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **188 <sub>(184–190)</sub>** | 216 <sub>(207–220)</sub> | 212 <sub>(206–216)</sub> | 13,178 <sub>(2,073–21,260)</sub> | 327 <sub>(312–358)</sub> | 212 <sub>(198–220)</sub> | 235 <sub>(224–239)</sub> | 231 <sub>(222–239)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **640 <sub>(616–661)</sub>** | 10,283 <sub>(5,319–14,509)</sub> | 8,140 <sub>(2,407–12,877)</sub> | 36,706 <sub>(33,998–37,790)</sub> | 27,041 <sub>(24,614–30,238)</sub> | 939 <sub>(720–2,590)</sub> | 29,006 <sub>(20,637–50,286)</sub> | 18,660 <sub>(15,674–49,671)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,037 <sub>(1,020–1,084)</sub>** | 13,016 <sub>(8,796–17,733)</sub> | 12,078 <sub>(4,211–17,733)</sub> | 37,715 <sub>(34,752–39,346)</sub> | 28,709 <sub>(25,896–32,558)</sub> | 1,659 <sub>(1,158–4,307)</sub> | 50,412 <sub>(35,661–73,975)</sub> | 38,045 <sub>(31,144–70,781)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 88.0% <sub>(85.9%–90.4%)</sub> | 88.7% <sub>(87.4%–93.3%)</sub> | 34.3% <sub>(21.7%–49.9%)</sub> | 68.6% <sub>(65.3%–70.1%)</sub> | 99.6% <sub>(94.1%–100.0%)</sub> | 84.8% <sub>(83.2%–87.0%)</sub> | 86.4% <sub>(83.4%–88.1%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 115 <sub>(100–130)</sub> | 105 <sub>(90–130)</sub> | 390 <sub>(300–440)</sub> | 215 <sub>(200–250)</sub> | 10 <sub>(0–40)</sub> | 250 <sub>(210–310)</sub> | 225 <sub>(210–310)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 24,480 | 17,381 <sub>(17,043–17,678)</sub> | 17,603 <sub>(17,259–17,893)</sub> | **10,552 <sub>(9,975–11,130)</sub>** | 12,375 <sub>(11,925–13,050)</sub> | 16,405 <sub>(15,330–19,350)</sub> | 18,862 <sub>(18,270–19,290)</sub> | 18,818 <sub>(18,510–19,155)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.60 <sub>(2.55–2.69)</sub> | 2.10 <sub>(2.04–2.16)</sub> | 2.11 <sub>(2.03–2.16)</sub> | 3.27 <sub>(2.39–5.21)</sub> | 1.90 <sub>(1.86–2.07)</sub> | **1.74 <sub>(1.61–2.20)</sub>** | 2.35 <sub>(2.23–2.49)</sub> | 2.30 <sub>(2.22–2.49)</sub> |
| Mean replicas | 24.0 | 17.0 <sub>(16.7–17.3)</sub> | 17.3 <sub>(16.9–17.5)</sub> | 10.3 <sub>(9.8–10.9)</sub> | 12.1 <sub>(11.7–12.8)</sub> | 16.1 <sub>(15.0–19.0)</sub> | 18.5 <sub>(17.9–18.9)</sub> | 18.4 <sub>(18.1–18.8)</sub> |
| Peak replicas | 24 | 32 | 32 <sub>(31–32)</sub> | 15 <sub>(14–16)</sub> | 18 <sub>(18–21)</sub> | 22 <sub>(18–31)</sub> | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 224 <sub>(154–367)</sub> | 196 <sub>(67–289)</sub> | 776 <sub>(687–811)</sub> | 551 <sub>(489–562)</sub> | 39 <sub>(20–101)</sub> | 376 <sub>(282–512)</sub> | 297 <sub>(274–512)</sub> |
| Scale-ups | 0 | 6 <sub>(5–7)</sub> | 6 <sub>(5–7)</sub> | 7 <sub>(7–8)</sub> | 8 <sub>(7–8)</sub> | 2 <sub>(1–3)</sub> | 6 <sub>(5–6)</sub> | 6 <sub>(5–7)</sub> |
| Scale-downs | 0 | 2 <sub>(2–4)</sub> | 4 <sub>(3–5)</sub> | 0 <sub>(0–1)</sub> | 2 <sub>(2–4)</sub> | 2 <sub>(1–4)</sub> | 4 <sub>(3–6)</sub> | 4 <sub>(2–5)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-rps` | `hpa-rps` |
| TTFT p95 (ms) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-cluster-like` | `cluster-like` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like` |
| Goodput (TTFT within the objective) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `predict-rps` | `hpa-rps` |
| Goodput (TTFT within the objective) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `cluster-like` | `hpa-rps`, `predict-rps` |
| Goodput (TTFT within the objective) | `predict-cluster-like` | `hpa-rps`, `predict-rps`, `cluster-like` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-rps` | `hpa-rps` |
| Seconds the service was unhealthy | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `cluster-like` | `hpa-rps` |
| Seconds the service was unhealthy | `predict-cluster-like` | `hpa-rps` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `predict-concurrency`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-concurrency` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `warm-12` | `static-24` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds (cost) | `predict-cluster-like` | `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-concurrency` | `static-24`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-rps` | `static-24`, `hpa-concurrency`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `warm-12` | `static-24`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `cluster-like` | `static-24` |
| Replica-seconds per good request | `predict-cluster-like` | `static-24`, `hpa-rps` |
