## The cluster against the simulation: a ramp from 3 to 20 requests per second over 120 s

Workload [ramp-120](../../workloads/ramp-120.json), 17 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 82.9% <sub>(82.1%–86.2%)</sub> | 88.3% <sub>(88.1%–90.4%)</sub> | 89.3% <sub>(88.8%–90.2%)</sub> | 80.5% <sub>(79.3%–81.2%)</sub> | 86.7% <sub>(85.0%–87.0%)</sub> | -5.4 points | -6.3 points | +2.4 points | -3.8 points |
| TTFT p50 (ms) | 230 <sub>(218–232)</sub> | 213 <sub>(207–220)</sub> | 224 <sub>(216–227)</sub> | 252 <sub>(244–261)</sub> | 235 <sub>(225–236)</sub> | +16 | +5 | -22 | -6 |
| TTFT p95 (ms) | 16,968 <sub>(16,355–23,269)</sub> | 8,965 <sub>(8,328–10,948)</sub> | 11,821 <sub>(9,504–15,499)</sub> | 40,800 <sub>(29,922–44,913)</sub> | 29,985 <sub>(20,637–38,964)</sub> | +8,003 | +5,147 | -23,832 | -13,017 |
| TTFT p99 (ms) | 30,328 <sub>(26,636–33,241)</sub> | 11,891 <sub>(10,547–15,091)</sub> | 26,387 <sub>(24,480–31,286)</sub> | 55,566 <sub>(51,354–70,974)</sub> | 59,512 <sub>(35,661–73,975)</sub> | +18,437 | +3,941 | -25,238 | -29,184 |
| Seconds the service was unhealthy | 250 | 120 <sub>(100–130)</sub> | 200 <sub>(160–210)</sub> | 320 <sub>(270–330)</sub> | 240 <sub>(210–260)</sub> | +130 | +50 | -70 | +10 |
| Replica-seconds (cost) | 18,254 <sub>(18,121–18,861)</sub> | 17,641 <sub>(17,107–17,678)</sub> | 18,118 <sub>(18,015–18,540)</sub> | 19,215 <sub>(19,170–19,215)</sub> | 18,855 <sub>(18,615–19,290)</sub> | +612 | +136 | -961 | -601 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 6 <sub>(6–7)</sub> | 6 <sub>(6–7)</sub> | 6 | 7 | 6 <sub>(5–6)</sub> | 0 | 0 | -1 | 0 |
| Scale-downs | 4 <sub>(2–6)</sub> | 2 <sub>(2–4)</sub> | 4 <sub>(3–5)</sub> | 4 | 5 <sub>(5–6)</sub> | +2 | 0 | 0 | -1 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 5 of 28,436.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 50.5% <sub>(50.4%–62.5%)</sub> | 72.0% <sub>(70.1%–79.0%)</sub> | 62.5% <sub>(61.4%–63.0%)</sub> | 44.5% <sub>(40.6%–45.4%)</sub> | 54.2% <sub>(50.6%–56.0%)</sub> | -21.5 points | -12.0 points | +6.0 points | -3.7 points |
| TTFT p50 (ms) | 1,671 <sub>(412–1,766)</sub> | 277 <sub>(247–295)</sub> | 435 <sub>(403–449)</sub> | 7,018 <sub>(5,077–13,426)</sub> | 809 <sub>(605–1,685)</sub> | +1,394 | +1,235 | -5,347 | +862 |
| TTFT p95 (ms) | 118,877 <sub>(62,164–119,781)</sub> | 21,743 <sub>(10,430–21,913)</sub> | 67,558 <sub>(64,504–71,692)</sub> | 145,174 <sub>(135,245–150,161)</sub> | 92,305 <sub>(84,952–111,625)</sub> | +97,134 | +51,319 | -26,298 | +26,572 |
| TTFT p99 (ms) | 134,481 <sub>(75,405–137,103)</sub> | 23,128 <sub>(11,191–23,552)</sub> | 82,958 <sub>(81,833–86,576)</sub> | 164,744 <sub>(145,159–186,081)</sub> | 104,463 <sub>(95,844–150,524)</sub> | +111,353 | +51,523 | -30,264 | +30,017 |
| Seconds the service was unhealthy | 520 <sub>(380–550)</sub> | 180 <sub>(130–190)</sub> | 400 <sub>(380–440)</sub> | 600 <sub>(560–620)</sub> | 490 <sub>(450–500)</sub> | +340 | +120 | -80 | +30 |
| Replica-seconds (cost) | 16,418 <sub>(15,360–16,763)</sub> | 17,850 <sub>(17,685–17,985)</sub> | 15,210 <sub>(14,775–15,990)</sub> | 14,520 <sub>(14,520–14,595)</sub> | 15,270 <sub>(15,045–16,305)</sub> | -1,432 | +1,208 | +1,898 | +1,148 |
| Peak pods | 28 <sub>(26–28)</sub> | 32 | 23 <sub>(23–26)</sub> | 25 <sub>(25–26)</sub> | 25 <sub>(24–27)</sub> | -4 | +5 | +3 | +3 |
| Scale-ups | 9 | 6 <sub>(6–10)</sub> | 6 <sub>(5–9)</sub> | 7 <sub>(5–7)</sub> | 9 <sub>(5–9)</sub> | +3 | +3 | +2 | 0 |
| Scale-downs | 3 <sub>(2–3)</sub> | 2 <sub>(1–5)</sub> | 4 <sub>(0–5)</sub> | 0 | 3 <sub>(0–3)</sub> | +1 | -1 | +3 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 3 of 28,436.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 99.6% <sub>(99.4%–99.8%)</sub> | 100.0% | 99.7% <sub>(99.7%–99.8%)</sub> | 99.7% <sub>(99.7%–99.8%)</sub> | 99.7% <sub>(99.7%–99.8%)</sub> | -0.4 points | -0.2 points | -0.2 points | -0.2 points |
| TTFT p50 (ms) | 186 <sub>(184–188)</sub> | 188 <sub>(187–190)</sub> | 201 <sub>(199–202)</sub> | 201 <sub>(199–202)</sub> | 201 <sub>(199–202)</sub> | -2 | -14 | -14 | -14 |
| TTFT p95 (ms) | 792 <sub>(784–793)</sub> | 648 <sub>(641–661)</sub> | 747 <sub>(743–772)</sub> | 747 <sub>(743–772)</sub> | 747 <sub>(743–772)</sub> | +144 | +45 | +45 | +45 |
| TTFT p99 (ms) | 1,441 <sub>(1,363–1,579)</sub> | 1,055 <sub>(1,028–1,084)</sub> | 1,276 <sub>(1,212–1,302)</sub> | 1,276 <sub>(1,212–1,302)</sub> | 1,276 <sub>(1,212–1,302)</sub> | +386 | +165 | +165 | +165 |
| Seconds the service was unhealthy | 0 <sub>(0–10)</sub> | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Replica-seconds (cost) | 24,480 | 24,480 | 24,480 | 24,480 | 24,480 | 0 | 0 | 0 | 0 |
| Peak pods | 24 | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 |
| Scale-ups | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 28,436.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 82.1% | 88.1% | 89.3% | 80.5% | 85.0% | 23,269 | 10,948 | 15,499 | 44,913 | 29,985 | 32 | 32 |
| `hpa-concurrency` | 2 | 82.9% | 88.3% | 88.8% | 79.3% | 86.7% | 16,355 | 8,965 | 11,821 | 29,922 | 38,964 | 32 | 32 |
| `hpa-concurrency` | 3 | 86.2% | 90.4% | 90.2% | 81.2% | 87.0% | 16,968 | 8,328 | 9,504 | 40,800 | 20,637 | 32 | 32 |
| `hpa-utilization` | 1 | 50.4% | 79.0% | 61.4% | 45.4% | 54.2% | 119,781 | 10,430 | 64,504 | 135,245 | 92,305 | 26 | 32 |
| `hpa-utilization` | 2 | 62.5% | 70.1% | 62.5% | 40.6% | 50.6% | 62,164 | 21,913 | 71,692 | 150,161 | 111,625 | 28 | 32 |
| `hpa-utilization` | 3 | 50.5% | 72.0% | 63.0% | 44.5% | 56.0% | 118,877 | 21,743 | 67,558 | 145,174 | 84,952 | 28 | 32 |
| `static-24` | 1 | 99.8% | 100.0% | 99.7% | 99.7% | 99.7% | 792 | 661 | 772 | 772 | 772 | 24 | 24 |
| `static-24` | 2 | 99.6% | 100.0% | 99.7% | 99.7% | 99.7% | 793 | 648 | 743 | 743 | 743 | 24 | 24 |
| `static-24` | 3 | 99.4% | 100.0% | 99.8% | 99.8% | 99.8% | 784 | 641 | 747 | 747 | 747 | 24 | 24 |
