## What does a shorter scale-down window cost, and what does it save?

Workload [burst](../../workloads/burst.json): 30 minutes, about 14,221 requests in a run. The objective is a first token within 2 s. A pool may grow to 32 pods.

Each cell is the median of 8 runs, with the lowest and highest in brackets. Every policy replays the same seeded trace in each run; the seeds differ between runs.

| Policy | Spec | Fewest pods | Pod startup | Decides every |
|---|---|---|---|---|
| `conc-down-300` | `conc-down-300=hpa-concurrency:down=300,route=pod` | 2 | 45 s | 15 s |
| `conc-down-120` | `conc-down-120=hpa-concurrency:down=120,route=pod` | 2 | 45 s | 15 s |
| `conc-down-60` | `conc-down-60=hpa-concurrency:down=60,route=pod` | 2 | 45 s | 15 s |
| `conc-down-30` | `conc-down-30=hpa-concurrency:down=30,route=pod` | 2 | 45 s | 15 s |
| `queue-down-300` | `queue-down-300=hpa-queue:down=300,route=pod` | 2 | 45 s | 15 s |
| `queue-down-60` | `queue-down-60=hpa-queue:down=60,route=pod` | 2 | 45 s | 15 s |

| Metric | `conc-down-300` | `conc-down-120` | `conc-down-60` | `conc-down-30` | `queue-down-300` | `queue-down-60` |
|---|---|---|---|---|---|---|
| TTFT p50 (ms) <sub>lower is better</sub> | **250 <sub>(240–262)</sub>** | 290 <sub>(270–325)</sub> | 317 <sub>(284–341)</sub> | 336 <sub>(286–366)</sub> | 258 <sub>(239–267)</sub> | 340 <sub>(297–425)</sub> |
| TTFT p95 (ms) <sub>lower is better</sub> | **79,368 <sub>(54,084–85,692)</sub>** | 110,209 <sub>(67,193–121,771)</sub> | 117,757 <sub>(80,557–192,419)</sub> | 131,392 <sub>(114,158–188,832)</sub> | 110,278 <sub>(20,704–237,269)</sub> | 200,815 <sub>(126,152–251,335)</sub> |
| TTFT p99 (ms) <sub>lower is better</sub> | **117,707 <sub>(110,475–169,624)</sub>** | 142,907 <sub>(112,525–170,332)</sub> | 167,777 <sub>(155,831–257,838)</sub> | 230,413 <sub>(142,251–269,428)</sub> | 211,626 <sub>(54,198–282,984)</sub> | 272,193 <sub>(183,626–308,069)</sub> |
| Goodput (TTFT within the objective) <sub>higher is better</sub> | **80.1% <sub>(78.7%–81.4%)</sub>** | 73.3% <sub>(68.4%–79.0%)</sub> | 69.8% <sub>(67.1%–77.0%)</sub> | 69.2% <sub>(65.9%–77.2%)</sub> | 79.3% <sub>(75.1%–82.8%)</sub> | 67.5% <sub>(63.3%–74.7%)</sub> |
| Seconds the service was unhealthy <sub>lower is better</sub> | **480 <sub>(410–530)</sub>** | 685 <sub>(540–820)</sub> | 770 <sub>(700–860)</sub> | 955 <sub>(780–1,110)</sub> | 515 <sub>(460–690)</sub> | 965 <sub>(920–1,040)</sub> |
| Replica-seconds (cost) <sub>lower is better</sub> | 35,475 <sub>(34,442–35,755)</sub> | 30,310 <sub>(28,790–32,615)</sub> | 28,272 <sub>(27,447–31,145)</sub> | **26,893 <sub>(25,784–28,699)</sub>** | 37,844 <sub>(35,502–48,057)</sub> | 34,477 <sub>(29,381–37,789)</sub> |
| Replica-seconds per good request <sub>lower is better</sub> | 3.10 <sub>(3.00–3.18)</sub> | 2.90 <sub>(2.56–3.31)</sub> | 2.85 <sub>(2.60–3.13)</sub> | **2.72 <sub>(2.35–3.07)</sub>** | 3.31 <sub>(3.07–4.33)</sub> | 3.47 <sub>(3.22–3.99)</sub> |
| Mean replicas | 19.7 <sub>(19.1–19.9)</sub> | 16.8 <sub>(16.0–18.1)</sub> | 15.7 <sub>(15.2–17.3)</sub> | 14.9 <sub>(14.3–15.9)</sub> | 21.0 <sub>(19.7–26.7)</sub> | 19.2 <sub>(16.3–21.0)</sub> |
| Peak replicas | 32 | 32 | 32 | 32 | 32 | 32 |
| Longest queue (requests) <sub>lower is better</sub> | 832 <sub>(811–859)</sub> | **828 <sub>(778–865)</sub>** | 874 <sub>(817–937)</sub> | 916 <sub>(817–942)</sub> | 918 <sub>(680–1,045)</sub> | 944 <sub>(827–1,162)</sub> |
| Scale-ups | 10 <sub>(9–12)</sub> | 14 <sub>(11–16)</sub> | 15 <sub>(14–18)</sub> | 18 <sub>(16–20)</sub> | 12 <sub>(11–15)</sub> | 24 <sub>(19–27)</sub> |
| Scale-downs | 8 <sub>(6–9)</sub> | 10 <sub>(8–15)</sub> | 16 <sub>(10–20)</sub> | 18 <sub>(14–24)</sub> | 4 <sub>(3–5)</sub> | 9 <sub>(9–11)</sub> |
| Flaps (a scale-up within 120 s of a scale-down) | 1 <sub>(0–2)</sub> | 7 <sub>(1–12)</sub> | 8 <sub>(6–9)</sub> | 15 <sub>(10–16)</sub> | 8 <sub>(6–10)</sub> | 19 <sub>(17–24)</sub> |

**Differences that held in every one of the 8 runs**

| Metric | Policy | Better than, in every run |
|---|---|---|
| TTFT p95 (ms) | `conc-down-300` | `conc-down-60`, `conc-down-30`, `queue-down-60` |
| TTFT p95 (ms) | `conc-down-120` | `queue-down-60` |
| Goodput (TTFT within the objective) | `conc-down-300` | `conc-down-120`, `conc-down-60`, `conc-down-30`, `queue-down-60` |
| Goodput (TTFT within the objective) | `queue-down-300` | `conc-down-60`, `conc-down-30`, `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-300` | `conc-down-120`, `conc-down-60`, `conc-down-30`, `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-120` | `conc-down-30`, `queue-down-60` |
| Seconds the service was unhealthy | `conc-down-60` | `queue-down-60` |
| Seconds the service was unhealthy | `queue-down-300` | `conc-down-60`, `conc-down-30`, `queue-down-60` |
| Replica-seconds (cost) | `conc-down-120` | `conc-down-300`, `queue-down-300` |
| Replica-seconds (cost) | `conc-down-60` | `conc-down-300`, `conc-down-120`, `queue-down-300` |
| Replica-seconds (cost) | `conc-down-30` | `conc-down-300`, `conc-down-120`, `queue-down-300`, `queue-down-60` |
| Replica-seconds per good request | `conc-down-300` | `queue-down-300`, `queue-down-60` |
| Replica-seconds per good request | `conc-down-120` | `queue-down-60` |
| Replica-seconds per good request | `conc-down-60` | `queue-down-60` |
| Replica-seconds per good request | `conc-down-30` | `queue-down-300`, `queue-down-60` |
