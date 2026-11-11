## Does scaling ahead of the load beat reacting to it? (ramp-600)

Workload [ramp-600](../../workloads/ramp-600.json): 25 minutes, about 14,914 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

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
| TTFT p50 (ms) <sub>lower is better</sub> | **186 <sub>(184–189)</sub>** | 221 <sub>(216–225)</sub> | 213 <sub>(210–218)</sub> | 360 <sub>(304–576)</sub> | 243 <sub>(235–277)</sub> | 209 <sub>(204–211)</sub> | 255 <sub>(231–281)</sub> | 241 <sub>(230–252)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **635 <sub>(612–645)</sub>** | 893 <sub>(800–1,124)</sub> | 782 <sub>(750–861)</sub> | 10,360 <sub>(4,807–15,336)</sub> | 1,300 <sub>(1,108–6,297)</sub> | 722 <sub>(698–877)</sub> | 3,377 <sub>(2,806–4,170)</sub> | 2,317 <sub>(1,957–3,271)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **1,020 <sub>(1,020–1,050)</sub>** | 1,774 <sub>(1,276–4,667)</sub> | 1,325 <sub>(1,276–1,986)</sub> | 12,866 <sub>(8,553–18,983)</sub> | 4,720 <sub>(2,542–9,796)</sub> | 1,151 <sub>(1,099–1,471)</sub> | 7,735 <sub>(5,988–10,623)</sub> | 5,919 <sub>(5,252–14,562)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **100.0%** | 99.2% <sub>(96.7%–99.9%)</sub> | 99.5% <sub>(99.0%–99.9%)</sub> | 79.0% <sub>(62.5%–85.6%)</sub> | 96.7% <sub>(90.8%–98.4%)</sub> | **100.0% <sub>(99.9%–100.0%)</sub>** | 91.8% <sub>(88.9%–92.4%)</sub> | 94.1% <sub>(92.8%–95.1%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **0** | 60 <sub>(20–110)</sub> | 40 <sub>(20–60)</sub> | 400 <sub>(290–560)</sub> | 120 <sub>(70–240)</sub> | **0 <sub>(0–10)</sub>** | 420 <sub>(300–630)</sub> | 360 <sub>(290–460)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 36,000 | 17,708 <sub>(16,505–19,901)</sub> | 18,428 <sub>(17,610–19,470)</sub> | **14,738 <sub>(13,920–15,285)</sub>** | 15,345 <sub>(14,820–16,350)</sub> | 21,660 <sub>(21,000–22,305)</sub> | 19,786 <sub>(19,020–22,602)</sub> | 20,081 <sub>(19,515–24,381)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 2.41 <sub>(2.40–2.45)</sub> | 1.20 <sub>(1.11–1.39)</sub> | 1.24 <sub>(1.18–1.32)</sub> | 1.25 <sub>(1.18–1.57)</sub> | **1.08 <sub>(1.04–1.13)</sub>** | 1.45 <sub>(1.41–1.50)</sub> | 1.45 <sub>(1.39–1.64)</sub> | 1.43 <sub>(1.38–1.76)</sub> |
| Mean replicas | 24.0 | 11.8 <sub>(11.0–13.3)</sub> | 12.3 <sub>(11.7–13.0)</sub> | 9.8 <sub>(9.3–10.2)</sub> | 10.2 <sub>(9.9–10.9)</sub> | 14.4 <sub>(14.0–14.9)</sub> | 13.2 <sub>(12.7–15.1)</sub> | 13.4 <sub>(13.0–16.3)</sub> |
| Peak replicas | 24 | 18 <sub>(16–20)</sub> | 18 <sub>(18–20)</sub> | 16 <sub>(14–16)</sub> | 16 <sub>(15–17)</sub> | 18 <sub>(17–20)</sub> | 22 <sub>(20–25)</sub> | 20 <sub>(19–26)</sub> |
| Longest queue (requests) <sub>lower is better</sub> | **1** | 22 <sub>(14–61)</sub> | 22 <sub>(10–27)</sub> | 152 <sub>(71–214)</sub> | 49 <sub>(27–101)</sub> | 14 <sub>(5–34)</sub> | 50 <sub>(36–83)</sub> | 39 <sub>(30–100)</sub> |
| Scale-ups | 0 | 8 <sub>(6–9)</sub> | 8 <sub>(6–9)</sub> | 9 <sub>(8–10)</sub> | 9 <sub>(8–10)</sub> | 2 <sub>(1–3)</sub> | 8 <sub>(7–10)</sub> | 7 <sub>(6–9)</sub> |
| Scale-downs | 0 | 2 <sub>(1–4)</sub> | 2 <sub>(1–4)</sub> | 0 <sub>(0–2)</sub> | 0 <sub>(0–2)</sub> | 2 <sub>(1–3)</sub> | 2 <sub>(1–5)</sub> | 2 <sub>(1–4)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 0 | 2 <sub>(0–3)</sub> | 0 <sub>(0–2)</sub> | 0 | 0 | 0 | 3 <sub>(0–8)</sub> | 2 <sub>(0–7)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-concurrency` | `hpa-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `predict-rps` | `hpa-rps` |
| TTFT p95 (ms) | `warm-12` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| TTFT p95 (ms) | `cluster-like` | `hpa-rps` |
| TTFT p95 (ms) | `predict-cluster-like` | `hpa-rps` |
| Goodput (TTFT within the objective) | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `hpa-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `predict-rps` | `hpa-rps`, `cluster-like` |
| Goodput (TTFT within the objective) | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Goodput (TTFT within the objective) | `cluster-like` | `hpa-rps` |
| Goodput (TTFT within the objective) | `predict-cluster-like` | `hpa-rps`, `cluster-like` |
| Seconds the service was unhealthy | `static-24` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `hpa-concurrency` | `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-concurrency` | `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `predict-rps` | `hpa-rps`, `cluster-like`, `predict-cluster-like` |
| Seconds the service was unhealthy | `warm-12` | `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `predict-rps`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-concurrency` | `static-24`, `warm-12`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-concurrency` | `static-24`, `warm-12`, `predict-cluster-like` |
| Replica-seconds (cost) | `hpa-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `predict-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds (cost) | `warm-12` | `static-24` |
| Replica-seconds (cost) | `cluster-like` | `static-24` |
| Replica-seconds (cost) | `predict-cluster-like` | `static-24` |
| Replica-seconds per good request | `hpa-concurrency` | `static-24`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `predict-concurrency` | `static-24`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `hpa-rps` | `static-24` |
| Replica-seconds per good request | `predict-rps` | `static-24`, `hpa-concurrency`, `predict-concurrency`, `hpa-rps`, `warm-12`, `cluster-like`, `predict-cluster-like` |
| Replica-seconds per good request | `warm-12` | `static-24` |
| Replica-seconds per good request | `cluster-like` | `static-24` |
| Replica-seconds per good request | `predict-cluster-like` | `static-24` |
