## Does scaling ahead of the load beat reacting to it? (burst)

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

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
| TTFT p50 (ms) <sub>lower is better</sub> | **190 <sub>(185–192)</sub>** | 243 <sub>(236–252)</sub> | 238 <sub>(229–245)</sub> | 673 <sub>(539–713)</sub> | 294 <sub>(280–296)</sub> | 225 <sub>(217–239)</sub> | 258 <sub>(250–270)</sub> | 254 <sub>(243–264)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **643 <sub>(623–676)</sub>** | 47,125 <sub>(40,499–50,987)</sub> | 47,125 <sub>(40,499–50,987)</sub> | 51,254 <sub>(49,939–53,056)</sub> | 50,608 <sub>(49,782–52,259)</sub> | 5,970 <sub>(4,085–7,076)</sub> | 97,044 <sub>(58,926–113,106)</sub> | 86,264 <sub>(69,317–113,106)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,065 <sub>(1,020–1,084)</sub>** | 61,179 <sub>(57,387–64,283)</sub> | 61,179 <sub>(57,387–64,283)</sub> | 65,725 <sub>(63,235–66,146)</sub> | 64,156 <sub>(62,832–64,564)</sub> | 20,160 <sub>(17,058–21,207)</sub> | 136,767 <sub>(111,816–169,292)</sub> | 143,328 <sub>(110,461–169,292)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 80.3% <sub>(79.9%–81.7%)</sub> | 80.3% <sub>(79.6%–82.2%)</sub> | 54.0% <sub>(53.1%–58.3%)</sub> | 71.5% <sub>(70.9%–73.8%)</sub> | 93.5% <sub>(91.2%–93.7%)</sub> | 77.3% <sub>(76.4%–78.8%)</sub> | 77.8% <sub>(77.4%–80.4%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 215 <sub>(180–240)</sub> | 215 <sub>(180–240)</sub> | 425 <sub>(380–470)</sub> | 300 <sub>(260–310)</sub> | 65 <sub>(60–110)</sub> | 545 <sub>(450–570)</sub> | 500 <sub>(440–560)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 43,200 | 32,053 <sub>(31,702–32,220)</sub> | 32,989 <sub>(32,426–33,696)</sub> | **18,469 <sub>(17,994–18,771)</sub>** | 26,001 <sub>(24,871–26,639)</sub> | 33,076 <sub>(31,445–34,198)</sub> | 36,338 <sub>(35,093–36,828)</sub> | 36,558 <sub>(35,723–37,158)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.04 <sub>(3.00–3.06)</sub> | 2.79 <sub>(2.72–2.83)</sub> | 2.86 <sub>(2.79–2.94)</sub> | **2.37 <sub>(2.24–2.48)</sub>** | 2.51 <sub>(2.48–2.60)</sub> | 2.49 <sub>(2.36–2.63)</sub> | 3.29 <sub>(3.13–3.32)</sub> | 3.28 <sub>(3.16–3.35)</sub> |
| Mean replicas | 24.0 | 17.8 <sub>(17.6–17.9)</sub> | 18.3 <sub>(18.0–18.7)</sub> | 10.3 <sub>(10.0–10.4)</sub> | 14.4 <sub>(13.8–14.8)</sub> | 18.4 <sub>(17.5–19.0)</sub> | 20.2 <sub>(19.5–20.5)</sub> | 20.3 <sub>(19.8–20.6)</sub> |
| Peak replicas | 24 | 32 | 32 | 15 <sub>(14–16)</sub> | 26 <sub>(24–27)</sub> | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | **18 <sub>(1–23)</sub>** | 838 <sub>(816–869)</sub> | 838 <sub>(816–869)</sub> | 916 <sub>(848–959)</sub> | 908 <sub>(848–959)</sub> | 434 <sub>(397–456)</sub> | 853 <sub>(814–896)</sub> | 856 <sub>(818–896)</sub> |
| Scale-ups | 0 | 10 <sub>(9–12)</sub> | 9 <sub>(8–10)</sub> | 7 <sub>(6–8)</sub> | 8 | 6 <sub>(4–7)</sub> | 9 <sub>(8–10)</sub> | 10 <sub>(7–11)</sub> |
| Scale-downs | 0 | 7 <sub>(6–7)</sub> | 8 <sub>(7–9)</sub> | 4 <sub>(3–4)</sub> | 9 <sub>(7–10)</sub> | 4 <sub>(4–5)</sub> | 6 <sub>(5–9)</sub> | 7 <sub>(4–11)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 1 <sub>(0–2)</sub> | 0 | 0 | 0 | 1 <sub>(1–3)</sub> | 0 <sub>(0–1)</sub> | 0 <sub>(0–3)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-rps` | `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-rps` | `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `predict-rps` | `hpa-rps` |
| Goodput (TTFT within the objective) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `cluster-like` | `hpa-rps`, `predict-rps` |
| Goodput (TTFT within the objective) | `predict-cluster-like` | `hpa-rps`, `predict-rps` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `hpa-rps` | `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-rps` | `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `predict-concurrency`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-concurrency` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `warm-12` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds (cost) | `predict-cluster-like` | `static-24` |
| Replica-seconds per good request | `static-24` | `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `predict-concurrency`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-concurrency` | `static-24`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `hpa-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `warm-12` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `cluster-like`, `predict-cluster-like` |
