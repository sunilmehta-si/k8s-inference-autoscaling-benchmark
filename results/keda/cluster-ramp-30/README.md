## KEDA beside the HPA on the cluster: a ramp from 3 to 20 requests per second over 30 s

Workload [ramp-30](../../workloads/ramp-30.json), 16 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets. A `keda-` run has KEDA in place of prometheus-adapter: KEDA's operator sums the recorded series in Prometheus, and the autoscaler it creates reads that sum as an external metric, averaged over every pod the Deployment has; its simulation is the same controller reading that metric.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 73.8% <sub>(72.9%–75.6%)</sub> | 79.2% <sub>(79.0%–80.0%)</sub> | 81.0% <sub>(79.0%–81.9%)</sub> | 70.8% <sub>(70.6%–71.2%)</sub> | 77.4% <sub>(75.1%–78.8%)</sub> | -5.4 points | -7.2 points | +3.0 points | -3.6 points |
| TTFT p50 (ms) | 264 <sub>(261–275)</sub> | 238 <sub>(237–248)</sub> | 245 <sub>(243–260)</sub> | 302 <sub>(295–306)</sub> | 262 <sub>(257–281)</sub> | +25 | +19 | -38 | +2 |
| TTFT p95 (ms) | 83,353 <sub>(31,917–92,047)</sub> | 26,063 <sub>(25,599–28,251)</sub> | 50,162 <sub>(46,564–53,605)</sub> | 93,886 <sub>(57,268–97,709)</sub> | 68,381 <sub>(67,717–102,528)</sub> | +57,290 | +33,192 | -10,533 | +14,972 |
| TTFT p99 (ms) | 105,424 <sub>(42,185–114,649)</sub> | 27,244 <sub>(27,162–30,999)</sub> | 71,210 <sub>(62,565–78,610)</sub> | 115,003 <sub>(69,265–116,591)</sub> | 89,595 <sub>(85,748–126,177)</sub> | +78,180 | +34,214 | -9,579 | +15,830 |
| Seconds the service was unhealthy | 340 <sub>(280–360)</sub> | 140 <sub>(120–150)</sub> | 230 <sub>(230–280)</sub> | 370 <sub>(340–380)</sub> | 290 <sub>(280–340)</sub> | +200 | +110 | -30 | +50 |
| Replica-seconds (cost) | 19,089 <sub>(18,277–19,336)</sub> | 16,650 <sub>(16,425–16,755)</sub> | 18,195 <sub>(18,195–18,225)</sub> | 19,440 <sub>(18,660–19,575)</sub> | 18,765 <sub>(18,645–19,650)</sub> | +2,439 | +894 | -351 | +324 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 5 <sub>(4–7)</sub> | 6 <sub>(5–6)</sub> | 5 | 6 <sub>(5–6)</sub> | 5 <sub>(4–5)</sub> | -1 | 0 | -1 | 0 |
| Scale-downs | 3 <sub>(3–4)</sub> | 3 <sub>(3–4)</sub> | 5 <sub>(5–6)</sub> | 2 <sub>(1–3)</sub> | 2 <sub>(2–3)</sub> | 0 | -2 | +1 | +1 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 7 of 25,296.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 46.4% <sub>(39.9%–48.6%)</sub> | 57.8% <sub>(55.8%–61.7%)</sub> | 52.5% <sub>(49.8%–52.6%)</sub> | 35.2% <sub>(31.9%–36.1%)</sub> | 43.8% <sub>(41.0%–45.5%)</sub> | -11.4 points | -6.1 points | +11.2 points | +2.6 points |
| TTFT p50 (ms) | 4,054 <sub>(3,141–11,875)</sub> | 458 <sub>(368–534)</sub> | 1,044 <sub>(1,042–2,075)</sub> | 36,521 <sub>(35,129–40,444)</sub> | 8,167 <sub>(5,307–16,219)</sub> | +3,595 | +3,009 | -32,467 | -4,114 |
| TTFT p95 (ms) | 128,900 <sub>(128,456–181,654)</sub> | 44,459 <sub>(34,976–45,340)</sub> | 127,330 <sub>(123,041–133,224)</sub> | 220,304 <sub>(219,511–226,597)</sub> | 181,658 <sub>(168,769–182,000)</sub> | +84,441 | +1,570 | -91,404 | -52,758 |
| TTFT p99 (ms) | 144,088 <sub>(137,043–211,090)</sub> | 45,633 <sub>(38,560–46,365)</sub> | 153,087 <sub>(134,971–173,885)</sub> | 238,269 <sub>(235,988–239,503)</sub> | 192,964 <sub>(189,596–198,104)</sub> | +98,455 | -8,999 | -94,181 | -48,875 |
| Seconds the service was unhealthy | 510 <sub>(440–560)</sub> | 210 <sub>(180–210)</sub> | 440 <sub>(430–500)</sub> | 610 <sub>(610–670)</sub> | 520 <sub>(510–560)</sub> | +300 | +70 | -100 | -10 |
| Replica-seconds (cost) | 13,726 <sub>(13,441–14,387)</sub> | 16,740 <sub>(16,695–16,755)</sub> | 14,325 <sub>(13,860–14,745)</sub> | 12,840 <sub>(12,330–13,125)</sub> | 13,755 <sub>(12,885–14,265)</sub> | -3,014 | -599 | +886 | -29 |
| Peak pods | 25 | 32 | 25 <sub>(24–26)</sub> | 26 <sub>(24–27)</sub> | 25 <sub>(24–27)</sub> | -7 | 0 | -1 | 0 |
| Scale-ups | 9 <sub>(9–10)</sub> | 6 <sub>(6–7)</sub> | 6 <sub>(5–6)</sub> | 6 | 8 <sub>(6–8)</sub> | +3 | +3 | +3 | +1 |
| Scale-downs | 1 <sub>(0–2)</sub> | 2 <sub>(2–4)</sub> | 2 <sub>(0–2)</sub> | 0 | 0 | -1 | -1 | +1 | +1 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 25,296.

### `keda-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 75.8% <sub>(73.5%–77.4%)</sub> | 79.2% <sub>(79.0%–80.0%)</sub> | 81.0% <sub>(79.0%–81.9%)</sub> | 70.8% <sub>(70.6%–71.2%)</sub> | 77.4% <sub>(75.1%–78.8%)</sub> | -3.3 points | -5.2 points | +5.1 points | -1.5 points |
| TTFT p50 (ms) | 256 <sub>(256–271)</sub> | 238 <sub>(237–248)</sub> | 245 <sub>(243–260)</sub> | 302 <sub>(295–306)</sub> | 262 <sub>(257–281)</sub> | +18 | +11 | -46 | -6 |
| TTFT p95 (ms) | 61,762 <sub>(23,009–87,266)</sub> | 26,063 <sub>(25,599–28,251)</sub> | 50,162 <sub>(46,564–53,605)</sub> | 93,886 <sub>(57,268–97,709)</sub> | 68,381 <sub>(67,717–102,528)</sub> | +35,699 | +11,600 | -32,124 | -6,620 |
| TTFT p99 (ms) | 82,460 <sub>(35,305–105,697)</sub> | 27,244 <sub>(27,162–30,999)</sub> | 71,210 <sub>(62,565–78,610)</sub> | 115,003 <sub>(69,265–116,591)</sub> | 89,595 <sub>(85,748–126,177)</sub> | +55,215 | +11,249 | -32,544 | -7,135 |
| Seconds the service was unhealthy | 310 <sub>(270–350)</sub> | 140 <sub>(120–150)</sub> | 230 <sub>(230–280)</sub> | 370 <sub>(340–380)</sub> | 290 <sub>(280–340)</sub> | +170 | +80 | -60 | +20 |
| Replica-seconds (cost) | 18,759 <sub>(18,094–18,786)</sub> | 16,650 <sub>(16,425–16,755)</sub> | 18,195 <sub>(18,195–18,225)</sub> | 19,440 <sub>(18,660–19,575)</sub> | 18,765 <sub>(18,645–19,650)</sub> | +2,109 | +564 | -681 | -6 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 5 | 6 <sub>(5–6)</sub> | 5 | 6 <sub>(5–6)</sub> | 5 <sub>(4–5)</sub> | -1 | 0 | -1 | 0 |
| Scale-downs | 3 <sub>(2–8)</sub> | 3 <sub>(3–4)</sub> | 5 <sub>(5–6)</sub> | 2 <sub>(1–3)</sub> | 2 <sub>(2–3)</sub> | 0 | -2 | +1 | +1 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 4 of 25,296.

### `keda-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 41.0% <sub>(38.6%–46.1%)</sub> | 57.8% <sub>(55.8%–61.7%)</sub> | 52.5% <sub>(49.8%–52.6%)</sub> | 35.2% <sub>(31.9%–36.1%)</sub> | 43.8% <sub>(41.0%–45.5%)</sub> | -16.8 points | -11.5 points | +5.8 points | -2.8 points |
| TTFT p50 (ms) | 12,126 <sub>(5,572–17,183)</sub> | 458 <sub>(368–534)</sub> | 1,044 <sub>(1,042–2,075)</sub> | 36,521 <sub>(35,129–40,444)</sub> | 8,167 <sub>(5,307–16,219)</sub> | +11,668 | +11,082 | -24,395 | +3,959 |
| TTFT p95 (ms) | 171,907 <sub>(126,131–201,596)</sub> | 44,459 <sub>(34,976–45,340)</sub> | 127,330 <sub>(123,041–133,224)</sub> | 220,304 <sub>(219,511–226,597)</sub> | 181,658 <sub>(168,769–182,000)</sub> | +127,448 | +44,577 | -48,398 | -9,751 |
| TTFT p99 (ms) | 206,057 <sub>(136,378–220,644)</sub> | 45,633 <sub>(38,560–46,365)</sub> | 153,087 <sub>(134,971–173,885)</sub> | 238,269 <sub>(235,988–239,503)</sub> | 192,964 <sub>(189,596–198,104)</sub> | +160,423 | +52,970 | -32,213 | +13,093 |
| Seconds the service was unhealthy | 560 <sub>(500–570)</sub> | 210 <sub>(180–210)</sub> | 440 <sub>(430–500)</sub> | 610 <sub>(610–670)</sub> | 520 <sub>(510–560)</sub> | +350 | +120 | -50 | +40 |
| Replica-seconds (cost) | 12,909 <sub>(12,449–14,475)</sub> | 16,740 <sub>(16,695–16,755)</sub> | 14,325 <sub>(13,860–14,745)</sub> | 12,840 <sub>(12,330–13,125)</sub> | 13,755 <sub>(12,885–14,265)</sub> | -3,831 | -1,416 | +69 | -846 |
| Peak pods | 23 <sub>(22–28)</sub> | 32 | 25 <sub>(24–26)</sub> | 26 <sub>(24–27)</sub> | 25 <sub>(24–27)</sub> | -9 | -2 | -3 | -2 |
| Scale-ups | 8 <sub>(6–8)</sub> | 6 <sub>(6–7)</sub> | 6 <sub>(5–6)</sub> | 6 | 8 <sub>(6–8)</sub> | +2 | +2 | +2 | 0 |
| Scale-downs | 0 <sub>(0–2)</sub> | 2 <sub>(2–4)</sub> | 2 <sub>(0–2)</sub> | 0 <sub>(0–1)</sub> | 0 | -2 | -2 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 25,296.

### KEDA against the HPA, on the cluster

Each signal run both ways on the same seeds: the HPA reading a pods metric through prometheus-adapter, and the HPA KEDA creates reading the sum over the pods as an external metric. A seed counts as better or worse when its two runs differ at all.

#### concurrency

Seeds 1, 2, 3.

| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 73.8% <sub>(72.9%–75.6%)</sub> | 75.8% <sub>(73.5%–77.4%)</sub> | +2.1 points | KEDA better in 2, worse in 1 of 3 |
| TTFT p50 (ms) | 264 <sub>(261–275)</sub> | 256 <sub>(256–271)</sub> | -7 | KEDA better in 2, worse in 1 of 3 |
| TTFT p95 (ms) | 83,353 <sub>(31,917–92,047)</sub> | 61,762 <sub>(23,009–87,266)</sub> | -21,592 | KEDA better in 2, worse in 1 of 3 |
| TTFT p99 (ms) | 105,424 <sub>(42,185–114,649)</sub> | 82,460 <sub>(35,305–105,697)</sub> | -22,965 | KEDA better in 2, worse in 1 of 3 |
| Seconds the service was unhealthy | 340 <sub>(280–360)</sub> | 310 <sub>(270–350)</sub> | -30 | KEDA better in 2, worse in 1 of 3 |
| Replica-seconds (cost) | 19,089 <sub>(18,277–19,336)</sub> | 18,759 <sub>(18,094–18,786)</sub> | -331 | KEDA better in 3, worse in 0 of 3 |
| Peak pods | 32 | 32 | 0 | KEDA higher in 0, lower in 0 of 3 |
| Scale-ups | 5 <sub>(4–7)</sub> | 5 | 0 | KEDA higher in 1, lower in 1 of 3 |
| Scale-downs | 3 <sub>(3–4)</sub> | 3 <sub>(2–8)</sub> | 0 | KEDA higher in 1, lower in 1 of 3 |
| Flaps | 0 | 0 | 0 | KEDA higher in 0, lower in 0 of 3 |

#### utilization

Seeds 1, 2, 3.

| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 46.4% <sub>(39.9%–48.6%)</sub> | 41.0% <sub>(38.6%–46.1%)</sub> | -5.4 points | KEDA better in 0, worse in 3 of 3 |
| TTFT p50 (ms) | 4,054 <sub>(3,141–11,875)</sub> | 12,126 <sub>(5,572–17,183)</sub> | +8,072 | KEDA better in 0, worse in 3 of 3 |
| TTFT p95 (ms) | 128,900 <sub>(128,456–181,654)</sub> | 171,907 <sub>(126,131–201,596)</sub> | +43,007 | KEDA better in 1, worse in 2 of 3 |
| TTFT p99 (ms) | 144,088 <sub>(137,043–211,090)</sub> | 206,057 <sub>(136,378–220,644)</sub> | +61,969 | KEDA better in 1, worse in 2 of 3 |
| Seconds the service was unhealthy | 510 <sub>(440–560)</sub> | 560 <sub>(500–570)</sub> | +50 | KEDA better in 1, worse in 2 of 3 |
| Replica-seconds (cost) | 13,726 <sub>(13,441–14,387)</sub> | 12,909 <sub>(12,449–14,475)</sub> | -818 | KEDA better in 2, worse in 1 of 3 |
| Peak pods | 25 | 23 <sub>(22–28)</sub> | -2 | KEDA higher in 1, lower in 2 of 3 |
| Scale-ups | 9 <sub>(9–10)</sub> | 8 <sub>(6–8)</sub> | -1 | KEDA higher in 0, lower in 3 of 3 |
| Scale-downs | 1 <sub>(0–2)</sub> | 0 <sub>(0–2)</sub> | -1 | KEDA higher in 1, lower in 1 of 3 |
| Flaps | 0 | 0 | 0 | KEDA higher in 0, lower in 0 of 3 |

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 73.8% | 79.2% | 81.0% | 70.8% | 77.4% | 83,353 | 26,063 | 53,605 | 97,709 | 68,381 | 32 | 32 |
| `hpa-concurrency` | 2 | 75.6% | 79.0% | 79.0% | 70.6% | 75.1% | 31,917 | 25,599 | 46,564 | 57,268 | 102,528 | 32 | 32 |
| `hpa-concurrency` | 3 | 72.9% | 80.0% | 81.9% | 71.2% | 78.8% | 92,047 | 28,251 | 50,162 | 93,886 | 67,717 | 32 | 32 |
| `hpa-utilization` | 1 | 46.4% | 61.7% | 52.5% | 36.1% | 43.8% | 128,456 | 34,976 | 133,224 | 220,304 | 181,658 | 25 | 32 |
| `hpa-utilization` | 2 | 48.6% | 55.8% | 49.8% | 31.9% | 41.0% | 128,900 | 45,340 | 127,330 | 226,597 | 182,000 | 25 | 32 |
| `hpa-utilization` | 3 | 39.9% | 57.8% | 52.6% | 35.2% | 45.5% | 181,654 | 44,459 | 123,041 | 219,511 | 168,769 | 25 | 32 |
| `keda-concurrency` | 1 | 73.5% | 79.2% | 81.0% | 70.8% | 77.4% | 87,266 | 26,063 | 53,605 | 97,709 | 68,381 | 32 | 32 |
| `keda-concurrency` | 2 | 77.4% | 79.0% | 79.0% | 70.6% | 75.1% | 23,009 | 25,599 | 46,564 | 57,268 | 102,528 | 32 | 32 |
| `keda-concurrency` | 3 | 75.8% | 80.0% | 81.9% | 71.2% | 78.8% | 61,762 | 28,251 | 50,162 | 93,886 | 67,717 | 32 | 32 |
| `keda-utilization` | 1 | 46.1% | 61.7% | 52.5% | 36.1% | 43.8% | 126,131 | 34,976 | 133,224 | 220,304 | 181,658 | 22 | 32 |
| `keda-utilization` | 2 | 41.0% | 55.8% | 49.8% | 31.9% | 41.0% | 171,907 | 45,340 | 127,330 | 226,597 | 182,000 | 28 | 32 |
| `keda-utilization` | 3 | 38.6% | 57.8% | 52.6% | 35.2% | 45.5% | 201,596 | 44,459 | 123,041 | 219,511 | 168,769 | 23 | 32 |
