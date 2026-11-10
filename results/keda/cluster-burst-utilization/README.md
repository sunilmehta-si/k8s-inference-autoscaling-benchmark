## Which part of the path? The HPA, the external HPA and KEDA on utilization: burst

Workload [burst](../../workloads/burst.json), 30 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets. A `keda-` run has KEDA in place of prometheus-adapter: KEDA's operator sums the recorded series in Prometheus, and the autoscaler it creates reads that sum as an external metric, averaged over every pod the Deployment has; its simulation is the same controller reading that metric. An `external-` run is the HPA reading that same sum from prometheus-adapter as an external metric: KEDA's arithmetic on the adapter's path, with the same simulation as a `keda-` run.

### `external-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 44.0% <sub>(42.7%–44.4%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–56.7%)</sub> | 38.3% <sub>(36.9%–42.9%)</sub> | 46.4% <sub>(41.4%–48.5%)</sub> | -28.3 points | -12.2 points | +5.8 points | -2.3 points |
| TTFT p50 (ms) | 6,026 <sub>(4,676–6,696)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(618–2,174)</sub> | 12,719 <sub>(5,984–17,260)</sub> | 4,250 <sub>(3,077–9,155)</sub> | +5,750 | +5,394 | -6,692 | +1,776 |
| TTFT p95 (ms) | 159,463 <sub>(134,785–163,388)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | 131,347 <sub>(124,645–134,152)</sub> | 140,077 <sub>(101,924–149,725)</sub> | +116,726 | +78,019 | +28,116 | +19,386 |
| TTFT p99 (ms) | 186,269 <sub>(155,338–202,392)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | 147,895 <sub>(137,607–163,297)</sub> | 166,528 <sub>(113,486–170,904)</sub> | +114,211 | +70,046 | +38,374 | +19,741 |
| Seconds the service was unhealthy | 930 <sub>(890–970)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(700–880)</sub> | 940 <sub>(910–960)</sub> | 890 <sub>(790–920)</sub> | +650 | +200 | -10 | +40 |
| Replica-seconds (cost) | 23,570 <sub>(23,489–23,753)</sub> | 28,037 <sub>(27,533–29,538)</sub> | 23,419 <sub>(22,926–24,022)</sub> | 21,887 <sub>(20,852–23,220)</sub> | 22,924 <sub>(22,798–23,944)</sub> | -4,468 | +151 | +1,682 | +646 |
| Peak pods | 26 <sub>(25–28)</sub> | 32 | 26 <sub>(23–27)</sub> | 23 <sub>(21–25)</sub> | 25 <sub>(24–27)</sub> | -6 | 0 | +3 | +1 |
| Scale-ups | 15 <sub>(14–15)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | 11 <sub>(9–12)</sub> | 14 <sub>(12–15)</sub> | +6 | +2 | +4 | +1 |
| Scale-downs | 6 <sub>(5–8)</sub> | 6 | 5 <sub>(5–7)</sub> | 7 <sub>(6–9)</sub> | 8 <sub>(6–8)</sub> | 0 | +1 | -1 | -2 |
| Flaps | 0 <sub>(0–1)</sub> | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 9 of 42,581.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 43.4% <sub>(41.4%–45.8%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–57.1%)</sub> | 38.3% <sub>(36.9%–42.9%)</sub> | 46.4% <sub>(41.4%–49.2%)</sub> | -29.0 points | -12.9 points | +5.1 points | -3.0 points |
| TTFT p50 (ms) | 6,301 <sub>(4,321–9,560)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(586–2,174)</sub> | 12,719 <sub>(5,984–17,260)</sub> | 4,250 <sub>(2,350–9,155)</sub> | +6,025 | +5,669 | -6,418 | +2,051 |
| TTFT p95 (ms) | 140,923 <sub>(130,437–151,005)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | 131,347 <sub>(124,645–134,152)</sub> | 140,077 <sub>(101,840–149,725)</sub> | +98,187 | +59,480 | +9,577 | +846 |
| TTFT p99 (ms) | 158,749 <sub>(155,657–172,835)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | 147,895 <sub>(137,607–163,297)</sub> | 166,528 <sub>(113,189–170,904)</sub> | +86,690 | +42,526 | +10,854 | -7,779 |
| Seconds the service was unhealthy | 910 <sub>(890–970)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(690–880)</sub> | 940 <sub>(910–960)</sub> | 890 <sub>(760–920)</sub> | +630 | +180 | -30 | +20 |
| Replica-seconds (cost) | 23,725 <sub>(21,651–24,134)</sub> | 28,037 <sub>(27,533–29,613)</sub> | 23,419 <sub>(22,926–24,022)</sub> | 21,887 <sub>(20,852–23,220)</sub> | 22,924 <sub>(22,798–24,214)</sub> | -4,313 | +306 | +1,837 | +800 |
| Peak pods | 27 <sub>(22–28)</sub> | 32 | 26 <sub>(23–27)</sub> | 23 <sub>(21–25)</sub> | 25 <sub>(24–27)</sub> | -5 | +1 | +4 | +2 |
| Scale-ups | 15 <sub>(12–15)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | 11 <sub>(9–12)</sub> | 14 <sub>(12–15)</sub> | +6 | +2 | +4 | +1 |
| Scale-downs | 6 <sub>(6–8)</sub> | 6 <sub>(5–6)</sub> | 5 <sub>(5–7)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(6–8)</sub> | 0 | +1 | -1 | -1 |
| Flaps | 1 <sub>(0–1)</sub> | 0 | 0 | 0 | 0 | +1 | +1 | +1 | +1 |

Requests the cluster did not answer: 9 of 42,581.

### `keda-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 41.3% <sub>(41.1%–44.1%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–56.7%)</sub> | 38.3% <sub>(36.9%–42.9%)</sub> | 46.4% <sub>(41.4%–48.5%)</sub> | -31.1 points | -15.0 points | +3.0 points | -5.1 points |
| TTFT p50 (ms) | 7,859 <sub>(6,294–10,240)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(618–2,174)</sub> | 12,719 <sub>(5,984–17,260)</sub> | 4,250 <sub>(3,077–9,155)</sub> | +7,583 | +7,227 | -4,860 | +3,609 |
| TTFT p95 (ms) | 162,641 <sub>(127,008–174,701)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | 131,347 <sub>(124,645–134,152)</sub> | 140,077 <sub>(101,924–149,725)</sub> | +119,905 | +81,198 | +31,295 | +22,564 |
| TTFT p99 (ms) | 184,364 <sub>(159,354–202,847)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | 147,895 <sub>(137,607–163,297)</sub> | 166,528 <sub>(113,486–170,904)</sub> | +112,305 | +68,141 | +36,469 | +17,836 |
| Seconds the service was unhealthy | 930 <sub>(920–930)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(700–880)</sub> | 940 <sub>(910–960)</sub> | 890 <sub>(790–920)</sub> | +650 | +200 | -10 | +40 |
| Replica-seconds (cost) | 22,441 <sub>(22,095–22,850)</sub> | 28,037 <sub>(27,533–29,538)</sub> | 23,419 <sub>(22,926–24,022)</sub> | 21,887 <sub>(20,852–23,220)</sub> | 22,924 <sub>(22,798–23,944)</sub> | -5,597 | -978 | +553 | -483 |
| Peak pods | 25 <sub>(24–26)</sub> | 32 | 26 <sub>(23–27)</sub> | 23 <sub>(21–25)</sub> | 25 <sub>(24–27)</sub> | -7 | -1 | +2 | 0 |
| Scale-ups | 15 <sub>(15–17)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | 11 <sub>(9–12)</sub> | 14 <sub>(12–15)</sub> | +6 | +2 | +4 | +1 |
| Scale-downs | 8 <sub>(7–8)</sub> | 6 | 5 <sub>(5–7)</sub> | 7 <sub>(6–9)</sub> | 8 <sub>(6–8)</sub> | +2 | +3 | +1 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 3 of 42,581.

### KEDA against the HPA, on the cluster

Each signal run both ways on the same seeds: the HPA reading a pods metric through prometheus-adapter, and the HPA KEDA creates reading the sum over the pods as an external metric. A seed counts as better or worse when its two runs differ at all.

#### utilization

Seeds 1, 2, 3.

| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 43.4% <sub>(41.4%–45.8%)</sub> | 41.3% <sub>(41.1%–44.1%)</sub> | -2.1 points | KEDA better in 0, worse in 3 of 3 |
| TTFT p50 (ms) | 6,301 <sub>(4,321–9,560)</sub> | 7,859 <sub>(6,294–10,240)</sub> | +1,558 | KEDA better in 1, worse in 2 of 3 |
| TTFT p95 (ms) | 140,923 <sub>(130,437–151,005)</sub> | 162,641 <sub>(127,008–174,701)</sub> | +21,718 | KEDA better in 1, worse in 2 of 3 |
| TTFT p99 (ms) | 158,749 <sub>(155,657–172,835)</sub> | 184,364 <sub>(159,354–202,847)</sub> | +25,615 | KEDA better in 0, worse in 3 of 3 |
| Seconds the service was unhealthy | 910 <sub>(890–970)</sub> | 930 <sub>(920–930)</sub> | +20 | KEDA better in 1, worse in 2 of 3 |
| Replica-seconds (cost) | 23,725 <sub>(21,651–24,134)</sub> | 22,441 <sub>(22,095–22,850)</sub> | -1,284 | KEDA better in 2, worse in 1 of 3 |
| Peak pods | 27 <sub>(22–28)</sub> | 25 <sub>(24–26)</sub> | -2 | KEDA higher in 1, lower in 2 of 3 |
| Scale-ups | 15 <sub>(12–15)</sub> | 15 <sub>(15–17)</sub> | 0 | KEDA higher in 2, lower in 0 of 3 |
| Scale-downs | 6 <sub>(6–8)</sub> | 8 <sub>(7–8)</sub> | +2 | KEDA higher in 2, lower in 0 of 3 |
| Flaps | 1 <sub>(0–1)</sub> | 0 | -1 | KEDA higher in 0, lower in 2 of 3 |

### The external HPA against the HPA, on the cluster

Each signal run both ways on the same seeds: the HPA reading a pods metric through prometheus-adapter, and the HPA reading the sum over the pods as an external metric from the same adapter. A seed counts as better or worse when its two runs differ at all.

#### utilization

Seeds 1, 2, 3.

| Metric | HPA | External HPA | External HPA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 43.4% <sub>(41.4%–45.8%)</sub> | 44.0% <sub>(42.7%–44.4%)</sub> | +0.7 points | External HPA better in 2, worse in 1 of 3 |
| TTFT p50 (ms) | 6,301 <sub>(4,321–9,560)</sub> | 6,026 <sub>(4,676–6,696)</sub> | -275 | External HPA better in 2, worse in 1 of 3 |
| TTFT p95 (ms) | 140,923 <sub>(130,437–151,005)</sub> | 159,463 <sub>(134,785–163,388)</sub> | +18,540 | External HPA better in 1, worse in 2 of 3 |
| TTFT p99 (ms) | 158,749 <sub>(155,657–172,835)</sub> | 186,269 <sub>(155,338–202,392)</sub> | +27,520 | External HPA better in 1, worse in 2 of 3 |
| Seconds the service was unhealthy | 910 <sub>(890–970)</sub> | 930 <sub>(890–970)</sub> | +20 | External HPA better in 1, worse in 1 of 3 |
| Replica-seconds (cost) | 23,725 <sub>(21,651–24,134)</sub> | 23,570 <sub>(23,489–23,753)</sub> | -155 | External HPA better in 1, worse in 2 of 3 |
| Peak pods | 27 <sub>(22–28)</sub> | 26 <sub>(25–28)</sub> | -1 | External HPA higher in 2, lower in 1 of 3 |
| Scale-ups | 15 <sub>(12–15)</sub> | 15 <sub>(14–15)</sub> | 0 | External HPA higher in 1, lower in 0 of 3 |
| Scale-downs | 6 <sub>(6–8)</sub> | 6 <sub>(5–8)</sub> | 0 | External HPA higher in 1, lower in 1 of 3 |
| Flaps | 1 <sub>(0–1)</sub> | 0 <sub>(0–1)</sub> | -1 | External HPA higher in 0, lower in 1 of 3 |

### KEDA against the external HPA, on the cluster

Each signal run both ways on the same seeds: the HPA reading the sum over the pods as an external metric from prometheus-adapter, and the HPA KEDA creates reading the same sum from KEDA. A seed counts as better or worse when its two runs differ at all.

#### utilization

Seeds 1, 2, 3.

| Metric | External HPA | KEDA | KEDA minus External HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 44.0% <sub>(42.7%–44.4%)</sub> | 41.3% <sub>(41.1%–44.1%)</sub> | -2.7 points | KEDA better in 0, worse in 3 of 3 |
| TTFT p50 (ms) | 6,026 <sub>(4,676–6,696)</sub> | 7,859 <sub>(6,294–10,240)</sub> | +1,833 | KEDA better in 0, worse in 3 of 3 |
| TTFT p95 (ms) | 159,463 <sub>(134,785–163,388)</sub> | 162,641 <sub>(127,008–174,701)</sub> | +3,178 | KEDA better in 1, worse in 2 of 3 |
| TTFT p99 (ms) | 186,269 <sub>(155,338–202,392)</sub> | 184,364 <sub>(159,354–202,847)</sub> | -1,905 | KEDA better in 1, worse in 2 of 3 |
| Seconds the service was unhealthy | 930 <sub>(890–970)</sub> | 930 <sub>(920–930)</sub> | 0 | KEDA better in 1, worse in 1 of 3 |
| Replica-seconds (cost) | 23,570 <sub>(23,489–23,753)</sub> | 22,441 <sub>(22,095–22,850)</sub> | -1,129 | KEDA better in 3, worse in 0 of 3 |
| Peak pods | 26 <sub>(25–28)</sub> | 25 <sub>(24–26)</sub> | -1 | KEDA higher in 1, lower in 2 of 3 |
| Scale-ups | 15 <sub>(14–15)</sub> | 15 <sub>(15–17)</sub> | 0 | KEDA higher in 2, lower in 0 of 3 |
| Scale-downs | 6 <sub>(5–8)</sub> | 8 <sub>(7–8)</sub> | +2 | KEDA higher in 2, lower in 1 of 3 |
| Flaps | 0 <sub>(0–1)</sub> | 0 | 0 | KEDA higher in 0, lower in 1 of 3 |

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `external-utilization` | 1 | 42.7% | 70.6% | 56.2% | 42.9% | 46.4% | 163,388 | 46,900 | 71,830 | 124,645 | 149,725 | 26 | 32 |
| `external-utilization` | 2 | 44.4% | 72.3% | 49.7% | 38.3% | 41.4% | 159,463 | 37,689 | 108,516 | 131,347 | 140,077 | 25 | 32 |
| `external-utilization` | 3 | 44.0% | 72.5% | 56.7% | 36.9% | 48.5% | 134,785 | 42,736 | 81,443 | 134,152 | 101,924 | 28 | 32 |
| `hpa-utilization` | 1 | 41.4% | 70.6% | 56.2% | 42.9% | 46.4% | 130,437 | 46,900 | 71,830 | 124,645 | 149,725 | 22 | 32 |
| `hpa-utilization` | 2 | 45.8% | 72.3% | 49.7% | 38.3% | 41.4% | 140,923 | 37,689 | 108,516 | 131,347 | 140,077 | 28 | 32 |
| `hpa-utilization` | 3 | 43.4% | 72.5% | 57.1% | 36.9% | 49.2% | 151,005 | 42,736 | 81,443 | 134,152 | 101,840 | 27 | 32 |
| `keda-utilization` | 1 | 41.3% | 70.6% | 56.2% | 42.9% | 46.4% | 174,701 | 46,900 | 71,830 | 124,645 | 149,725 | 24 | 32 |
| `keda-utilization` | 2 | 44.1% | 72.3% | 49.7% | 38.3% | 41.4% | 127,008 | 37,689 | 108,516 | 131,347 | 140,077 | 26 | 32 |
| `keda-utilization` | 3 | 41.1% | 72.5% | 56.7% | 36.9% | 48.5% | 162,641 | 42,736 | 81,443 | 134,152 | 101,924 | 25 | 32 |
