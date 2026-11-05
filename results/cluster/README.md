## The cluster against the simulation: burst

Workload [burst](../../workloads/burst.json), 30 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and two runs of the simulation on the same trace with the same settings: one with a single shared queue, and one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Cluster minus one queue | Cluster minus queue per pod |
|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 76.4% <sub>(74.7%–79.4%)</sub> | 81.5% <sub>(80.0%–81.7%)</sub> | 81.0% <sub>(78.7%–81.4%)</sub> | -5.1 points | -4.6 points |
| TTFT p50 (ms) | 244 <sub>(240–260)</sub> | 241 <sub>(236–249)</sub> | 248 <sub>(240–261)</sub> | +3 | -4 |
| TTFT p95 (ms) | 121,236 <sub>(63,796–146,543)</sub> | 44,566 <sub>(43,021–49,684)</sub> | 84,696 <sub>(57,884–85,692)</sub> | +76,671 | +36,540 |
| TTFT p99 (ms) | 159,481 <sub>(122,955–172,367)</sub> | 58,808 <sub>(58,597–62,832)</sub> | 118,100 <sub>(115,964–153,440)</sub> | +100,673 | +41,381 |
| Seconds the service was unhealthy | 630 <sub>(510–630)</sub> | 210 <sub>(190–230)</sub> | 450 <sub>(410–530)</sub> | +420 | +180 |
| Replica-seconds (cost) | 36,713 <sub>(34,697–37,795)</sub> | 32,062 <sub>(31,702–32,196)</sub> | 35,126 <sub>(34,442–35,755)</sub> | +4,651 | +1,587 |
| Peak pods | 32 | 32 | 32 | 0 | 0 |
| Scale-ups | 10 <sub>(9–11)</sub> | 11 <sub>(9–11)</sub> | 9 <sub>(9–12)</sub> | -1 | +1 |
| Scale-downs | 6 <sub>(4–6)</sub> | 7 | 8 <sub>(6–9)</sub> | -1 | -2 |
| Flaps | 0 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(0–1)</sub> | -1 | -1 |

Requests the cluster did not answer: 31 of 42,581.

### `hpa-queue`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Cluster minus one queue | Cluster minus queue per pod |
|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 70.3% <sub>(64.1%–80.6%)</sub> | 64.3% <sub>(62.3%–73.6%)</sub> | 79.9% <sub>(75.1%–81.5%)</sub> | +6.0 points | -9.6 points |
| TTFT p50 (ms) | 294 <sub>(236–354)</sub> | 349 <sub>(306–376)</sub> | 247 <sub>(239–267)</sub> | -55 | +47 |
| TTFT p95 (ms) | 88,182 <sub>(60,822–135,626)</sub> | 54,415 <sub>(48,625–57,560)</sub> | 115,062 <sub>(105,495–126,675)</sub> | +33,767 | -26,880 |
| TTFT p99 (ms) | 141,153 <sub>(79,754–271,153)</sub> | 55,577 <sub>(54,293–68,072)</sub> | 246,769 <sub>(176,484–264,245)</sub> | +85,575 | -105,616 |
| Seconds the service was unhealthy | 600 <sub>(580–610)</sub> | 370 <sub>(330–420)</sub> | 510 <sub>(510–690)</sub> | +230 | +90 |
| Replica-seconds (cost) | 39,038 <sub>(37,623–42,609)</sub> | 31,860 <sub>(29,952–33,902)</sub> | 39,025 <sub>(37,502–44,854)</sub> | +7,178 | +13 |
| Peak pods | 32 | 32 | 32 | 0 | 0 |
| Scale-ups | 14 <sub>(14–15)</sub> | 14 <sub>(13–14)</sub> | 12 <sub>(11–15)</sub> | 0 | +2 |
| Scale-downs | 4 <sub>(4–5)</sub> | 3 | 4 <sub>(3–5)</sub> | +1 | 0 |
| Flaps | 8 <sub>(7–10)</sub> | 7 <sub>(5–10)</sub> | 7 <sub>(6–9)</sub> | +1 | +1 |

Requests the cluster did not answer: 64 of 42,581.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Cluster minus one queue | Cluster minus queue per pod |
|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 40.9% <sub>(38.4%–43.3%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–57.1%)</sub> | -31.5 points | -15.4 points |
| TTFT p50 (ms) | 7,712 <sub>(6,641–12,068)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(586–2,174)</sub> | +7,435 | +7,079 |
| TTFT p95 (ms) | 165,317 <sub>(145,420–202,576)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | +122,581 | +83,874 |
| TTFT p99 (ms) | 196,320 <sub>(168,843–245,266)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | +124,261 | +80,096 |
| Seconds the service was unhealthy | 970 <sub>(960–990)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(690–880)</sub> | +690 | +240 |
| Replica-seconds (cost) | 23,028 <sub>(22,726–23,394)</sub> | 28,037 <sub>(27,533–29,613)</sub> | 23,419 <sub>(22,926–24,022)</sub> | -5,009 | -391 |
| Peak pods | 26 <sub>(26–28)</sub> | 32 | 26 <sub>(23–27)</sub> | -6 | 0 |
| Scale-ups | 15 <sub>(13–18)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | +6 | +2 |
| Scale-downs | 7 <sub>(6–8)</sub> | 6 <sub>(5–6)</sub> | 5 <sub>(5–7)</sub> | +1 | +2 |
| Flaps | 1 <sub>(0–2)</sub> | 0 | 0 | +1 | +1 |

Requests the cluster did not answer: 5 of 42,581.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | One shared queue | Queue per pod | Cluster minus one queue | Cluster minus queue per pod |
|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 97.7% <sub>(97.3%–98.1%)</sub> | 100.0% | 98.4% <sub>(97.9%–98.6%)</sub> | -2.3 points | -0.7 points |
| TTFT p50 (ms) | 188 <sub>(185–192)</sub> | 190 <sub>(185–191)</sub> | 201 <sub>(199–203)</sub> | -3 | -13 |
| TTFT p95 (ms) | 1,038 <sub>(956–1,083)</sub> | 642 <sub>(623–644)</sub> | 914 <sub>(881–933)</sub> | +396 | +124 |
| TTFT p99 (ms) | 3,430 <sub>(2,918–4,243)</sub> | 1,036 <sub>(1,020–1,077)</sub> | 2,886 <sub>(2,533–3,715)</sub> | +2,395 | +544 |
| Seconds the service was unhealthy | 30 <sub>(20–50)</sub> | 0 | 30 <sub>(20–30)</sub> | +30 | 0 |
| Replica-seconds (cost) | 43,200 | 43,200 | 43,200 | 0 | 0 |
| Peak pods | 24 | 24 | 24 | 0 | 0 |
| Scale-ups | 0 | 0 | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 42,581.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 74.7% | 80.0% | 78.7% | 146,543 | 43,021 | 84,696 | 32 | 32 |
| `hpa-concurrency` | 2 | 79.4% | 81.7% | 81.0% | 63,796 | 44,566 | 57,884 | 32 | 32 |
| `hpa-concurrency` | 3 | 76.4% | 81.5% | 81.4% | 121,236 | 49,684 | 85,692 | 32 | 32 |
| `hpa-queue` | 1 | 80.6% | 62.3% | 79.9% | 135,626 | 54,415 | 115,062 | 32 | 32 |
| `hpa-queue` | 2 | 64.1% | 73.6% | 75.1% | 60,822 | 48,625 | 126,675 | 32 | 32 |
| `hpa-queue` | 3 | 70.3% | 64.3% | 81.5% | 88,182 | 57,560 | 105,495 | 32 | 32 |
| `hpa-utilization` | 1 | 40.9% | 70.6% | 56.2% | 202,576 | 46,900 | 71,830 | 26 | 32 |
| `hpa-utilization` | 2 | 38.4% | 72.3% | 49.7% | 145,420 | 37,689 | 108,516 | 28 | 32 |
| `hpa-utilization` | 3 | 43.3% | 72.5% | 57.1% | 165,317 | 42,736 | 81,443 | 26 | 32 |
| `static-24` | 1 | 97.7% | 100.0% | 97.9% | 1,038 | 642 | 933 | 24 | 24 |
| `static-24` | 2 | 97.3% | 100.0% | 98.4% | 1,083 | 644 | 914 | 24 | 24 |
| `static-24` | 3 | 98.1% | 100.0% | 98.6% | 956 | 623 | 881 | 24 | 24 |
