## Does scaling ahead of the load beat reacting to it? (ramp-30)

Workload [ramp-30](../../workloads/ramp-30.json): 16 minutes, about 8,383 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

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
| TTFT p50 (ms) <sub>lower is better</sub> | **189 <sub>(184–191)</sub>** | 240 <sub>(231–249)</sub> | 239 <sub>(231–249)</sub> | 13,213 <sub>(8,491–28,663)</sub> | 360 <sub>(328–443)</sub> | 213 <sub>(206–218)</sub> | 265 <sub>(255–304)</sub> | 259 <sub>(248–304)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **642 <sub>(621–662)</sub>** | 26,107 <sub>(21,587–31,511)</sub> | 26,107 <sub>(13,278–31,511)</sub> | 43,557 <sub>(41,682–45,168)</sub> | 41,776 <sub>(39,259–45,124)</sub> | 1,096 <sub>(785–2,451)</sub> | 71,849 <sub>(47,703–127,651)</sub> | 68,049 <sub>(47,011–127,651)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,050 <sub>(1,020–1,084)</sub>** | 27,955 <sub>(23,249–32,912)</sub> | 27,955 <sub>(16,784–32,912)</sub> | 45,047 <sub>(43,568–48,248)</sub> | 43,822 <sub>(42,422–48,248)</sub> | 1,821 <sub>(1,227–4,076)</sub> | 93,627 <sub>(67,330–155,053)</sub> | 88,820 <sub>(62,924–155,053)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 79.5% <sub>(78.1%–80.5%)</sub> | 79.9% <sub>(78.1%–83.5%)</sub> | 33.5% <sub>(18.5%–40.3%)</sub> | 64.7% <sub>(60.5%–68.1%)</sub> | 99.4% <sub>(92.1%–100.0%)</sub> | 76.7% <sub>(70.6%–78.8%)</sub> | 77.8% <sub>(70.6%–78.9%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 130 <sub>(110–150)</sub> | 125 <sub>(110–150)</sub> | 325 <sub>(300–420)</sub> | 190 <sub>(170–220)</sub> | 10 <sub>(0–50)</sub> | 310 <sub>(260–430)</sub> | 295 <sub>(260–430)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 22,320 | 16,568 <sub>(16,425–16,998)</sub> | 16,688 <sub>(16,560–17,280)</sub> | **9,795 <sub>(9,195–9,990)</sub>** | 11,925 <sub>(11,295–12,315)</sub> | 15,292 <sub>(14,070–17,865)</sub> | 19,125 <sub>(18,480–19,650)</sub> | 18,840 <sub>(18,405–19,650)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.66 <sub>(2.62–2.76)</sub> | 2.50 <sub>(2.46–2.56)</sub> | 2.50 <sub>(2.46–2.56)</sub> | 3.52 <sub>(2.98–5.92)</sub> | 2.18 <sub>(2.11–2.35)</sub> | **1.85 <sub>(1.65–2.32)</sub>** | 2.95 <sub>(2.80–3.39)</sub> | 2.88 <sub>(2.79–3.39)</sub> |
| Mean replicas | 24.0 | 17.8 <sub>(17.7–18.3)</sub> | 17.9 <sub>(17.8–18.6)</sub> | 10.5 <sub>(9.9–10.7)</sub> | 12.8 <sub>(12.1–13.2)</sub> | 16.4 <sub>(15.1–19.2)</sub> | 20.6 <sub>(19.9–21.1)</sub> | 20.3 <sub>(19.8–21.1)</sub> |
| Peak replicas | 24 | 32 | 32 | 15 <sub>(14–16)</sub> | 20 <sub>(19–21)</sub> | 21 <sub>(17–30)</sub> | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 597 <sub>(508–668)</sub> | 597 <sub>(342–668)</sub> | 932 <sub>(858–959)</sub> | 930 <sub>(857–956)</sub> | 40 <sub>(14–89)</sub> | 736 <sub>(587–1,007)</sub> | 717 <sub>(567–1,007)</sub> |
| Scale-ups | 0 | 6 <sub>(5–7)</sub> | 6 <sub>(5–7)</sub> | 5 <sub>(3–5)</sub> | 5 <sub>(4–5)</sub> | 2 <sub>(1–3)</sub> | 5 <sub>(4–5)</sub> | 5 <sub>(4–6)</sub> |
| Scale-downs | 0 | 4 <sub>(2–5)</sub> | 4 <sub>(3–5)</sub> | 0 <sub>(0–2)</sub> | 4 <sub>(2–4)</sub> | 3 <sub>(1–5)</sub> | 3 <sub>(0–4)</sub> | 3 <sub>(0–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-rps` | `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-rps` | `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like` |
| Goodput (TTFT within the objective) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like` |
| Goodput (TTFT within the objective) | `predict-rps` | `hpa-rps` |
| Goodput (TTFT within the objective) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `cluster-like` | `hpa-rps`, `predict-rps` |
| Goodput (TTFT within the objective) | `predict-cluster-like` | `hpa-rps`, `predict-rps` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-rps` | `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-concurrency` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `warm-12` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds (cost) | `predict-cluster-like` | `static-24` |
| Replica-seconds per good request | `static-24` | `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-concurrency` | `static-24`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `warm-12` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
