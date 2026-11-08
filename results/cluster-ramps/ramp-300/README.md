## The cluster against the simulation: a ramp from 3 to 20 requests per second over 300 s

Workload [ramp-300](../../workloads/ramp-300.json), 20 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 89.9% <sub>(88.0%–92.7%)</sub> | 94.7% <sub>(93.9%–97.5%)</sub> | 91.0% <sub>(91.0%–93.2%)</sub> | 89.8% <sub>(88.7%–89.8%)</sub> | 91.1% <sub>(88.4%–92.3%)</sub> | -4.8 points | -1.1 points | +0.1 points | -1.2 points |
| TTFT p50 (ms) | 218 <sub>(210–248)</sub> | 222 <sub>(212–226)</sub> | 254 <sub>(234–265)</sub> | 231 <sub>(225–257)</sub> | 238 <sub>(231–253)</sub> | -4 | -36 | -13 | -20 |
| TTFT p95 (ms) | 4,759 <sub>(4,385–11,974)</sub> | 2,057 <sub>(1,276–2,987)</sub> | 3,493 <sub>(3,235–3,512)</sub> | 7,356 <sub>(5,128–14,067)</sub> | 4,190 <sub>(3,415–7,690)</sub> | +2,702 | +1,266 | -2,598 | +569 |
| TTFT p99 (ms) | 17,374 <sub>(15,434–31,652)</sub> | 3,852 <sub>(2,534–6,678)</sub> | 7,158 <sub>(5,859–11,778)</sub> | 20,340 <sub>(11,137–40,375)</sub> | 18,942 <sub>(6,313–22,375)</sub> | +13,522 | +10,216 | -2,966 | -1,568 |
| Seconds the service was unhealthy | 310 <sub>(230–410)</sub> | 100 <sub>(70–120)</sub> | 320 <sub>(260–400)</sub> | 300 <sub>(270–320)</sub> | 290 <sub>(260–310)</sub> | +210 | -10 | +10 | +20 |
| Replica-seconds (cost) | 20,629 <sub>(16,427–21,766)</sub> | 16,499 <sub>(15,240–17,443)</sub> | 16,395 <sub>(15,765–17,370)</sub> | 20,580 <sub>(15,834–20,590)</sub> | 18,797 <sub>(16,860–22,964)</sub> | +4,131 | +4,234 | +49 | +1,833 |
| Peak pods | 29 <sub>(19–32)</sub> | 23 <sub>(18–25)</sub> | 19 <sub>(19–20)</sub> | 31 <sub>(20–32)</sub> | 26 <sub>(23–30)</sub> | +6 | +10 | -2 | +3 |
| Scale-ups | 8 <sub>(6–8)</sub> | 7 <sub>(7–8)</sub> | 7 <sub>(6–8)</sub> | 8 <sub>(7–8)</sub> | 8 <sub>(8–9)</sub> | +1 | +1 | 0 | 0 |
| Scale-downs | 4 <sub>(2–4)</sub> | 2 <sub>(1–2)</sub> | 3 <sub>(1–3)</sub> | 3 <sub>(3–4)</sub> | 1 <sub>(1–2)</sub> | +2 | +1 | +1 | +3 |
| Flaps | 6 <sub>(0–6)</sub> | 0 <sub>(0–1)</sub> | 0 | 0 <sub>(0–1)</sub> | 1 <sub>(0–2)</sub> | +6 | +6 | +6 | +5 |

Requests the cluster did not answer: 27 of 34,610.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 76.8% <sub>(76.1%–85.8%)</sub> | 98.9% <sub>(95.5%–99.7%)</sub> | 91.3% <sub>(87.6%–91.4%)</sub> | 68.3% <sub>(65.9%–77.9%)</sub> | 82.4% <sub>(78.3%–88.7%)</sub> | -22.1 points | -14.4 points | +8.6 points | -5.5 points |
| TTFT p50 (ms) | 293 <sub>(257–306)</sub> | 212 <sub>(211–220)</sub> | 260 <sub>(255–261)</sub> | 372 <sub>(310–389)</sub> | 291 <sub>(259–304)</sub> | +81 | +33 | -78 | +2 |
| TTFT p95 (ms) | 23,051 <sub>(5,730–23,509)</sub> | 869 <sub>(805–1,608)</sub> | 3,897 <sub>(3,526–6,356)</sub> | 35,802 <sub>(17,647–51,295)</sub> | 16,064 <sub>(5,921–19,500)</sub> | +22,182 | +19,154 | -12,751 | +6,987 |
| TTFT p99 (ms) | 42,401 <sub>(10,588–58,823)</sub> | 2,151 <sub>(1,341–6,306)</sub> | 12,607 <sub>(11,163–24,063)</sub> | 57,058 <sub>(33,557–59,988)</sub> | 27,440 <sub>(15,785–30,217)</sub> | +40,250 | +29,794 | -14,657 | +14,962 |
| Seconds the service was unhealthy | 420 <sub>(390–500)</sub> | 30 <sub>(30–80)</sub> | 350 <sub>(300–360)</sub> | 480 <sub>(410–500)</sub> | 380 <sub>(360–390)</sub> | +390 | +70 | -60 | +40 |
| Replica-seconds (cost) | 17,101 <sub>(16,196–17,176)</sub> | 15,930 <sub>(15,885–17,310)</sub> | 16,365 <sub>(16,320–16,680)</sub> | 17,040 <sub>(17,025–17,805)</sub> | 16,050 <sub>(16,035–17,790)</sub> | +1,171 | +736 | +61 | +1,051 |
| Peak pods | 22 <sub>(20–22)</sub> | 20 <sub>(19–22)</sub> | 20 <sub>(20–22)</sub> | 23 <sub>(23–27)</sub> | 20 <sub>(20–23)</sub> | +2 | +2 | -1 | +2 |
| Scale-ups | 8 <sub>(8–11)</sub> | 9 <sub>(8–9)</sub> | 9 <sub>(6–9)</sub> | 9 <sub>(5–11)</sub> | 9 <sub>(8–10)</sub> | -1 | -1 | -1 | -1 |
| Scale-downs | 1 <sub>(0–2)</sub> | 2 <sub>(0–4)</sub> | 2 <sub>(0–3)</sub> | 2 <sub>(0–5)</sub> | 1 | -1 | -1 | -1 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 3 of 34,610.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 99.4% <sub>(99.4%–99.7%)</sub> | 100.0% | 99.8% <sub>(99.8%–99.9%)</sub> | 99.8% <sub>(99.8%–99.9%)</sub> | 99.8% <sub>(99.8%–99.9%)</sub> | -0.6 points | -0.4 points | -0.4 points | -0.4 points |
| TTFT p50 (ms) | 185 <sub>(183–188)</sub> | 187 <sub>(186–189)</sub> | 199 <sub>(198–200)</sub> | 199 <sub>(198–200)</sub> | 199 <sub>(198–200)</sub> | -2 | -14 | -14 | -14 |
| TTFT p95 (ms) | 773 <sub>(758–790)</sub> | 636 <sub>(636–637)</sub> | 730 <sub>(724–734)</sub> | 730 <sub>(724–734)</sub> | 730 <sub>(724–734)</sub> | +137 | +43 | +43 | +43 |
| TTFT p99 (ms) | 1,494 <sub>(1,299–1,554)</sub> | 1,020 <sub>(1,020–1,037)</sub> | 1,212 <sub>(1,198–1,212)</sub> | 1,212 <sub>(1,198–1,212)</sub> | 1,212 <sub>(1,198–1,212)</sub> | +474 | +282 | +282 | +282 |
| Seconds the service was unhealthy | 10 | 0 | 0 | 0 | 0 | +10 | +10 | +10 | +10 |
| Replica-seconds (cost) | 28,800 | 28,800 | 28,800 | 28,800 | 28,800 | 0 | 0 | 0 | 0 |
| Peak pods | 24 | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 |
| Scale-ups | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 34,610.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 88.0% | 93.9% | 93.2% | 88.7% | 88.4% | 11,974 | 2,987 | 3,493 | 14,067 | 7,690 | 32 | 23 |
| `hpa-concurrency` | 2 | 89.9% | 94.7% | 91.0% | 89.8% | 92.3% | 4,385 | 2,057 | 3,235 | 5,128 | 4,190 | 19 | 25 |
| `hpa-concurrency` | 3 | 92.7% | 97.5% | 91.0% | 89.8% | 91.1% | 4,759 | 1,276 | 3,512 | 7,356 | 3,415 | 29 | 18 |
| `hpa-utilization` | 1 | 76.1% | 98.9% | 91.4% | 68.3% | 78.3% | 23,051 | 869 | 3,897 | 51,295 | 19,500 | 22 | 22 |
| `hpa-utilization` | 2 | 76.8% | 95.5% | 87.6% | 65.9% | 82.4% | 23,509 | 1,608 | 6,356 | 35,802 | 16,064 | 20 | 20 |
| `hpa-utilization` | 3 | 85.8% | 99.7% | 91.3% | 77.9% | 88.7% | 5,730 | 805 | 3,526 | 17,647 | 5,921 | 22 | 19 |
| `static-24` | 1 | 99.7% | 100.0% | 99.8% | 99.8% | 99.8% | 758 | 637 | 734 | 734 | 734 | 24 | 24 |
| `static-24` | 2 | 99.4% | 100.0% | 99.8% | 99.8% | 99.8% | 773 | 636 | 730 | 730 | 730 | 24 | 24 |
| `static-24` | 3 | 99.4% | 100.0% | 99.9% | 99.9% | 99.9% | 790 | 636 | 724 | 724 | 724 | 24 | 24 |
