## Does scaling ahead of the load beat reacting to it? (ramp-300)

Workload [ramp-300](../../workloads/ramp-300.json): 20 minutes, about 11,492 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

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
| TTFT p50 (ms) <sub>lower is better</sub> | **187 <sub>(184–189)</sub>** | 222 <sub>(208–226)</sub> | 213 <sub>(205–217)</sub> | 3,761 <sub>(894–11,702)</sub> | 295 <sub>(271–325)</sub> | 207 <sub>(205–213)</sub> | 236 <sub>(225–253)</sub> | 230 <sub>(220–234)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **632 <sub>(610–646)</sub>** | 2,286 <sub>(1,276–3,653)</sub> | 976 <sub>(760–2,261)</sub> | 24,581 <sub>(18,426–26,378)</sub> | 12,315 <sub>(8,552–15,702)</sub> | 717 <sub>(690–2,275)</sub> | 5,002 <sub>(3,253–12,690)</sub> | 2,932 <sub>(2,272–6,338)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,027 <sub>(1,020–1,055)</sub>** | 5,004 <sub>(2,534–9,041)</sub> | 2,623 <sub>(1,340–5,116)</sub> | 26,397 <sub>(19,065–28,075)</sub> | 15,734 <sub>(11,625–18,337)</sub> | 1,157 <sub>(1,117–3,661)</sub> | 18,895 <sub>(6,313–28,471)</sub> | 10,462 <sub>(6,431–26,231)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 94.6% <sub>(92.1%–97.5%)</sub> | 98.4% <sub>(94.5%–99.7%)</sub> | 46.8% <sub>(30.7%–52.5%)</sub> | 80.4% <sub>(74.1%–86.2%)</sub> | **100.0% <sub>(93.5%–100.0%)</sub>** | 90.9% <sub>(86.0%–92.4%)</sub> | 93.5% <sub>(90.7%–94.4%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 100 <sub>(70–120)</sub> | 65 <sub>(30–100)</sub> | 420 <sub>(400–530)</sub> | 250 <sub>(200–290)</sub> | **0 <sub>(0–50)</sub>** | 300 <sub>(260–320)</sub> | 265 <sub>(220–320)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 28,800 | 16,536 <sub>(15,024–18,497)</sub> | 15,698 <sub>(14,925–17,185)</sub> | **12,082 <sub>(11,415–12,645)</sub>** | 13,072 <sub>(12,525–13,605)</sub> | 17,685 <sub>(16,860–21,435)</sub> | 19,865 <sub>(16,860–23,129)</sub> | 19,301 <sub>(16,635–22,228)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.51 <sub>(2.46–2.55)</sub> | 1.52 <sub>(1.34–1.73)</sub> | **1.40 <sub>(1.28–1.58)</sub>** | 2.20 <sub>(1.96–3.43)</sub> | 1.43 <sub>(1.30–1.51)</sub> | 1.55 <sub>(1.47–1.97)</sub> | 1.90 <sub>(1.58–2.38)</sub> | 1.80 <sub>(1.52–2.12)</sub> |
| Mean replicas | 24.0 | 13.8 <sub>(12.5–15.4)</sub> | 13.1 <sub>(12.4–14.3)</sub> | 10.1 <sub>(9.5–10.5)</sub> | 10.9 <sub>(10.4–11.3)</sub> | 14.7 <sub>(14.1–17.9)</sub> | 16.6 <sub>(14.1–19.3)</sub> | 16.1 <sub>(13.9–18.5)</sub> |
| Peak replicas | 24 | 22 <sub>(17–31)</sub> | 20 <sub>(17–23)</sub> | 15 <sub>(14–16)</sub> | 16 <sub>(15–17)</sub> | 18 <sub>(16–31)</sub> | 28 <sub>(20–32)</sub> | 25 <sub>(20–32)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 84 <sub>(32–119)</sub> | 31 <sub>(14–63)</sub> | 454 <sub>(367–557)</sub> | 178 <sub>(110–199)</sub> | 11 <sub>(4–90)</sub> | 130 <sub>(46–202)</sub> | 82 <sub>(38–140)</sub> |
| Scale-ups | 0 | 7 <sub>(5–9)</sub> | 7 <sub>(6–9)</sub> | 8 <sub>(7–9)</sub> | 9 <sub>(8–9)</sub> | 2 <sub>(2–3)</sub> | 8 <sub>(6–11)</sub> | 8 <sub>(7–9)</sub> |
| Scale-downs | 0 | 2 <sub>(1–4)</sub> | 2 <sub>(1–5)</sub> | 0 <sub>(0–2)</sub> | 1 <sub>(0–3)</sub> | 2 <sub>(0–3)</sub> | 2 <sub>(1–3)</sub> | 2 <sub>(1–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 0 <sub>(0–1)</sub> | 0 <sub>(0–1)</sub> | 0 | 0 | 0 | 1 <sub>(0–3)</sub> | 0 <sub>(0–8)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like` |
| TTFT p95 (ms) | `predict-concurrency` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-rps` | `hpa-rps` |
| TTFT p95 (ms) | `warm-12` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like` |
| TTFT p95 (ms) | `cluster-like` | `hpa-rps` |
| TTFT p95 (ms) | `predict-cluster-like` | `hpa-rps`, `predict-rps` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like` |
| Goodput (TTFT within the objective) | `predict-concurrency` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `predict-rps` | `hpa-rps` |
| Goodput (TTFT within the objective) | `warm-12` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like` |
| Goodput (TTFT within the objective) | `cluster-like` | `hpa-rps` |
| Goodput (TTFT within the objective) | `predict-cluster-like` | `hpa-rps`, `predict-rps`, `cluster-like` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-concurrency` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-rps` | `hpa-rps` |
| Seconds the service was unhealthy | `warm-12` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `cluster-like` | `hpa-rps` |
| Seconds the service was unhealthy | `predict-cluster-like` | `hpa-rps` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24` |
| Replica-seconds (cost) | `predict-concurrency` | `static-24`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `warm-12` | `static-24` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds (cost) | `predict-cluster-like` | `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `hpa-rps`, `cluster-like` |
| Replica-seconds per good request | `predict-concurrency` | `static-24`, `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-rps` | `static-24`, `hpa-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `warm-12` | `static-24`, `hpa-rps` |
| Replica-seconds per good request | `cluster-like` | `static-24` |
| Replica-seconds per good request | `predict-cluster-like` | `static-24` |
