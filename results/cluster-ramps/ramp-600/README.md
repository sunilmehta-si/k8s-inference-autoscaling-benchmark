## The cluster against the simulation: a ramp from 3 to 20 requests per second over 600 s

Workload [ramp-600](../../workloads/ramp-600.json), 25 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 89.8% <sub>(89.6%–92.2%)</sub> | 99.1% <sub>(96.7%–99.9%)</sub> | 92.7% <sub>(91.8%–93.6%)</sub> | 91.1% <sub>(90.5%–91.8%)</sub> | 91.6% <sub>(88.9%–92.4%)</sub> | -9.3 points | -2.8 points | -1.3 points | -1.8 points |
| TTFT p50 (ms) | 230 <sub>(215–235)</sub> | 222 <sub>(216–225)</sub> | 246 <sub>(246–250)</sub> | 260 <sub>(243–266)</sub> | 257 <sub>(254–281)</sub> | +9 | -16 | -29 | -27 |
| TTFT p95 (ms) | 4,495 <sub>(3,077–7,339)</sub> | 938 <sub>(844–1,124)</sub> | 2,741 <sub>(2,385–3,308)</sub> | 3,806 <sub>(3,317–3,895)</sub> | 3,153 <sub>(2,856–3,603)</sub> | +3,557 | +1,754 | +689 | +1,342 |
| TTFT p99 (ms) | 9,604 <sub>(9,534–24,810)</sub> | 1,887 <sub>(1,276–4,667)</sub> | 5,808 <sub>(5,770–8,253)</sub> | 8,633 <sub>(7,150–9,339)</sub> | 7,349 <sub>(6,520–8,631)</sub> | +7,718 | +3,796 | +971 | +2,255 |
| Seconds the service was unhealthy | 370 <sub>(350–430)</sub> | 60 <sub>(20–110)</sub> | 420 <sub>(420–450)</sub> | 510 <sub>(400–580)</sub> | 430 <sub>(410–630)</sub> | +310 | -50 | -140 | -60 |
| Replica-seconds (cost) | 21,639 <sub>(19,338–26,769)</sub> | 17,806 <sub>(16,505–19,901)</sub> | 19,905 <sub>(19,425–20,243)</sub> | 19,186 <sub>(19,155–20,770)</sub> | 19,204 <sub>(19,035–19,742)</sub> | +3,833 | +1,734 | +2,453 | +2,435 |
| Peak pods | 24 <sub>(22–28)</sub> | 18 <sub>(16–19)</sub> | 24 <sub>(20–24)</sub> | 19 <sub>(19–21)</sub> | 21 <sub>(20–22)</sub> | +6 | 0 | +5 | +3 |
| Scale-ups | 9 | 9 <sub>(8–9)</sub> | 9 <sub>(7–10)</sub> | 8 <sub>(8–10)</sub> | 9 <sub>(8–9)</sub> | 0 | 0 | +1 | 0 |
| Scale-downs | 6 <sub>(3–8)</sub> | 4 <sub>(2–4)</sub> | 4 <sub>(1–5)</sub> | 3 <sub>(0–4)</sub> | 2 <sub>(1–4)</sub> | +2 | +2 | +3 | +4 |
| Flaps | 6 <sub>(0–7)</sub> | 2 <sub>(2–3)</sub> | 0 <sub>(0–3)</sub> | 2 <sub>(0–4)</sub> | 3 <sub>(0–3)</sub> | +4 | +6 | +4 | +3 |

Requests the cluster did not answer: 10 of 44,614.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 94.2% <sub>(94.0%–94.3%)</sub> | 99.9% <sub>(99.1%–99.9%)</sub> | 93.9% <sub>(93.7%–94.5%)</sub> | 91.1% <sub>(90.2%–91.6%)</sub> | 94.7% <sub>(91.3%–94.7%)</sub> | -5.7 points | +0.3 points | +3.1 points | -0.6 points |
| TTFT p50 (ms) | 233 <sub>(230–233)</sub> | 209 <sub>(206–209)</sub> | 242 <sub>(241–252)</sub> | 260 <sub>(257–269)</sub> | 249 <sub>(237–257)</sub> | +24 | -9 | -27 | -16 |
| TTFT p95 (ms) | 2,279 <sub>(2,199–2,314)</sub> | 745 <sub>(740–769)</sub> | 2,366 <sub>(2,162–2,468)</sub> | 3,112 <sub>(2,929–3,747)</sub> | 2,109 <sub>(2,102–3,565)</sub> | +1,535 | -87 | -833 | +170 |
| TTFT p99 (ms) | 5,331 <sub>(5,150–5,681)</sub> | 1,212 <sub>(1,212–1,606)</sub> | 5,336 <sub>(4,753–7,298)</sub> | 6,457 <sub>(5,554–9,946)</sub> | 5,099 <sub>(5,040–9,279)</sub> | +4,119 | -6 | -1,127 | +231 |
| Seconds the service was unhealthy | 460 <sub>(390–470)</sub> | 20 <sub>(10–40)</sub> | 400 <sub>(320–420)</sub> | 560 <sub>(540–620)</sub> | 340 <sub>(340–450)</sub> | +440 | +60 | -100 | +120 |
| Replica-seconds (cost) | 20,134 <sub>(20,080–21,104)</sub> | 19,515 <sub>(19,065–20,552)</sub> | 19,950 <sub>(19,005–21,405)</sub> | 20,100 <sub>(19,020–20,190)</sub> | 19,830 <sub>(19,560–20,310)</sub> | +619 | +184 | +34 | +304 |
| Peak pods | 21 <sub>(21–24)</sub> | 21 <sub>(20–21)</sub> | 22 <sub>(19–23)</sub> | 22 <sub>(20–24)</sub> | 21 <sub>(20–22)</sub> | 0 | -1 | -1 | 0 |
| Scale-ups | 9 <sub>(7–9)</sub> | 10 <sub>(8–10)</sub> | 9 | 9 <sub>(9–10)</sub> | 9 <sub>(6–10)</sub> | -1 | 0 | 0 | 0 |
| Scale-downs | 1 <sub>(1–2)</sub> | 2 <sub>(2–3)</sub> | 2 <sub>(1–4)</sub> | 1 <sub>(0–2)</sub> | 1 <sub>(0–3)</sub> | -1 | -1 | 0 | 0 |
| Flaps | 0 | 0 <sub>(0–4)</sub> | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 1 of 44,614.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 99.6% <sub>(99.6%–99.6%)</sub> | 100.0% | 99.8% <sub>(99.7%–99.8%)</sub> | 99.8% <sub>(99.7%–99.8%)</sub> | 99.8% <sub>(99.7%–99.8%)</sub> | -0.4 points | -0.2 points | -0.2 points | -0.2 points |
| TTFT p50 (ms) | 183 <sub>(182–185)</sub> | 186 <sub>(185–188)</sub> | 196 <sub>(196–198)</sub> | 196 <sub>(196–198)</sub> | 196 <sub>(196–198)</sub> | -2 | -13 | -13 | -13 |
| TTFT p95 (ms) | 737 <sub>(736–768)</sub> | 637 <sub>(633–645)</sub> | 720 <sub>(708–737)</sub> | 720 <sub>(708–737)</sub> | 720 <sub>(708–737)</sub> | +99 | +16 | +16 | +16 |
| TTFT p99 (ms) | 1,279 <sub>(1,266–1,374)</sub> | 1,020 <sub>(1,020–1,038)</sub> | 1,212 <sub>(1,148–1,212)</sub> | 1,212 <sub>(1,148–1,212)</sub> | 1,212 <sub>(1,148–1,212)</sub> | +259 | +67 | +67 | +67 |
| Seconds the service was unhealthy | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Replica-seconds (cost) | 36,000 | 36,000 | 36,000 | 36,000 | 36,000 | 0 | 0 | 0 | 0 |
| Peak pods | 24 | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 |
| Scale-ups | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 44,614.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 89.6% | 96.7% | 92.7% | 90.5% | 88.9% | 7,339 | 1,124 | 2,741 | 3,317 | 3,603 | 28 | 18 |
| `hpa-concurrency` | 2 | 89.8% | 99.1% | 91.8% | 91.1% | 92.4% | 4,495 | 938 | 3,308 | 3,806 | 2,856 | 24 | 19 |
| `hpa-concurrency` | 3 | 92.2% | 99.9% | 93.6% | 91.8% | 91.6% | 3,077 | 844 | 2,385 | 3,895 | 3,153 | 22 | 16 |
| `hpa-utilization` | 1 | 94.3% | 99.1% | 93.9% | 90.2% | 91.3% | 2,199 | 769 | 2,468 | 3,747 | 3,565 | 21 | 21 |
| `hpa-utilization` | 2 | 94.2% | 99.9% | 93.7% | 91.1% | 94.7% | 2,314 | 740 | 2,366 | 3,112 | 2,102 | 21 | 20 |
| `hpa-utilization` | 3 | 94.0% | 99.9% | 94.5% | 91.6% | 94.7% | 2,279 | 745 | 2,162 | 2,929 | 2,109 | 24 | 21 |
| `static-24` | 1 | 99.6% | 100.0% | 99.7% | 99.7% | 99.7% | 736 | 633 | 720 | 720 | 720 | 24 | 24 |
| `static-24` | 2 | 99.6% | 100.0% | 99.8% | 99.8% | 99.8% | 768 | 645 | 737 | 737 | 737 | 24 | 24 |
| `static-24` | 3 | 99.6% | 100.0% | 99.8% | 99.8% | 99.8% | 737 | 637 | 708 | 708 | 708 | 24 | 24 |
