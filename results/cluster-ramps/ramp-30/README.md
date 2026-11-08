## The cluster against the simulation: a ramp from 3 to 20 requests per second over 30 s

Workload [ramp-30](../../workloads/ramp-30.json), 16 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and three runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; and one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag |
|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 73.5% <sub>(73.5%–76.3%)</sub> | 79.2% <sub>(79.0%–80.0%)</sub> | 81.0% <sub>(79.0%–81.9%)</sub> | 70.8% <sub>(70.6%–71.2%)</sub> | -5.6 points | -7.5 points | +2.8 points |
| TTFT p50 (ms) | 267 <sub>(253–277)</sub> | 238 <sub>(237–248)</sub> | 245 <sub>(243–260)</sub> | 302 <sub>(295–306)</sub> | +29 | +23 | -35 |
| TTFT p95 (ms) | 73,106 <sub>(66,741–87,431)</sub> | 26,063 <sub>(25,599–28,251)</sub> | 50,162 <sub>(46,564–53,605)</sub> | 93,886 <sub>(57,268–97,709)</sub> | +47,043 | +22,944 | -20,780 |
| TTFT p99 (ms) | 87,988 <sub>(87,775–107,839)</sub> | 27,244 <sub>(27,162–30,999)</sub> | 71,210 <sub>(62,565–78,610)</sub> | 115,003 <sub>(69,265–116,591)</sub> | +60,743 | +16,777 | -27,016 |
| Seconds the service was unhealthy | 330 <sub>(320–360)</sub> | 140 <sub>(120–150)</sub> | 230 <sub>(230–280)</sub> | 370 <sub>(340–380)</sub> | +190 | +100 | -40 |
| Replica-seconds (cost) | 18,981 <sub>(18,696–19,397)</sub> | 16,650 <sub>(16,425–16,755)</sub> | 18,195 <sub>(18,195–18,225)</sub> | 19,440 <sub>(18,660–19,575)</sub> | +2,331 | +786 | -459 |
| Peak pods | 32 | 32 | 32 | 32 | 0 | 0 | 0 |
| Scale-ups | 5 <sub>(5–6)</sub> | 6 <sub>(5–6)</sub> | 5 | 6 <sub>(5–6)</sub> | -1 | 0 | -1 |
| Scale-downs | 4 <sub>(3–4)</sub> | 3 <sub>(3–4)</sub> | 5 <sub>(5–6)</sub> | 2 <sub>(1–3)</sub> | +1 | -1 | +2 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 6 of 25,296.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag |
|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 42.8% <sub>(37.8%–43.6%)</sub> | 57.8% <sub>(55.8%–61.7%)</sub> | 52.5% <sub>(49.8%–52.6%)</sub> | 35.2% <sub>(31.9%–36.1%)</sub> | -15.0 points | -9.7 points | +7.6 points |
| TTFT p50 (ms) | 9,414 <sub>(7,486–16,004)</sub> | 458 <sub>(368–534)</sub> | 1,044 <sub>(1,042–2,075)</sub> | 36,521 <sub>(35,129–40,444)</sub> | +8,956 | +8,370 | -27,107 |
| TTFT p95 (ms) | 194,567 <sub>(178,667–210,311)</sub> | 44,459 <sub>(34,976–45,340)</sub> | 127,330 <sub>(123,041–133,224)</sub> | 220,304 <sub>(219,511–226,597)</sub> | +150,108 | +67,237 | -25,738 |
| TTFT p99 (ms) | 206,017 <sub>(202,765–229,787)</sub> | 45,633 <sub>(38,560–46,365)</sub> | 153,087 <sub>(134,971–173,885)</sub> | 238,269 <sub>(235,988–239,503)</sub> | +160,384 | +52,931 | -32,252 |
| Seconds the service was unhealthy | 570 <sub>(490–580)</sub> | 210 <sub>(180–210)</sub> | 440 <sub>(430–500)</sub> | 610 <sub>(610–670)</sub> | +360 | +130 | -40 |
| Replica-seconds (cost) | 13,857 <sub>(13,416–14,798)</sub> | 16,740 <sub>(16,695–16,755)</sub> | 14,325 <sub>(13,860–14,745)</sub> | 12,840 <sub>(12,330–13,125)</sub> | -2,883 | -468 | +1,017 |
| Peak pods | 27 <sub>(25–28)</sub> | 32 | 25 <sub>(24–26)</sub> | 26 <sub>(24–27)</sub> | -5 | +2 | +1 |
| Scale-ups | 6 <sub>(6–8)</sub> | 6 <sub>(6–7)</sub> | 6 <sub>(5–6)</sub> | 6 | 0 | 0 | 0 |
| Scale-downs | 1 <sub>(1–3)</sub> | 2 <sub>(2–4)</sub> | 2 <sub>(0–2)</sub> | 0 | -1 | -1 | +1 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 1 of 25,296.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag |
|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 99.4% <sub>(99.2%–99.5%)</sub> | 100.0% | 99.7% <sub>(99.6%–99.7%)</sub> | 99.7% <sub>(99.6%–99.7%)</sub> | -0.6 points | -0.3 points | -0.3 points |
| TTFT p50 (ms) | 188 <sub>(187–189)</sub> | 189 <sub>(189–191)</sub> | 200 <sub>(199–203)</sub> | 200 <sub>(199–203)</sub> | -1 | -12 | -12 |
| TTFT p95 (ms) | 826 <sub>(819–889)</sub> | 656 <sub>(641–662)</sub> | 774 <sub>(764–777)</sub> | 774 <sub>(764–777)</sub> | +171 | +53 | +53 |
| TTFT p99 (ms) | 1,536 <sub>(1,459–1,842)</sub> | 1,069 <sub>(1,048–1,084)</sub> | 1,277 <sub>(1,276–1,340)</sub> | 1,277 <sub>(1,276–1,340)</sub> | +467 | +259 | +259 |
| Seconds the service was unhealthy | 0 <sub>(0–20)</sub> | 0 | 0 <sub>(0–10)</sub> | 0 <sub>(0–10)</sub> | 0 | 0 | 0 |
| Replica-seconds (cost) | 22,320 | 22,320 | 22,320 | 22,320 | 0 | 0 | 0 |
| Peak pods | 24 | 24 | 24 | 24 | 0 | 0 | 0 |
| Scale-ups | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 25,296.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 76.3% | 79.2% | 81.0% | 70.8% | 73,106 | 26,063 | 53,605 | 97,709 | 32 | 32 |
| `hpa-concurrency` | 2 | 73.5% | 79.0% | 79.0% | 70.6% | 66,741 | 25,599 | 46,564 | 57,268 | 32 | 32 |
| `hpa-concurrency` | 3 | 73.5% | 80.0% | 81.9% | 71.2% | 87,431 | 28,251 | 50,162 | 93,886 | 32 | 32 |
| `hpa-utilization` | 1 | 42.8% | 61.7% | 52.5% | 36.1% | 194,567 | 34,976 | 133,224 | 220,304 | 25 | 32 |
| `hpa-utilization` | 2 | 43.6% | 55.8% | 49.8% | 31.9% | 178,667 | 45,340 | 127,330 | 226,597 | 28 | 32 |
| `hpa-utilization` | 3 | 37.8% | 57.8% | 52.6% | 35.2% | 210,311 | 44,459 | 123,041 | 219,511 | 27 | 32 |
| `static-24` | 1 | 99.5% | 100.0% | 99.6% | 99.6% | 819 | 662 | 777 | 777 | 24 | 24 |
| `static-24` | 2 | 99.2% | 100.0% | 99.7% | 99.7% | 889 | 656 | 774 | 774 | 24 | 24 |
| `static-24` | 3 | 99.4% | 100.0% | 99.7% | 99.7% | 826 | 641 | 764 | 764 | 24 | 24 |
