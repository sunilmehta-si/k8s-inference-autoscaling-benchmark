## The cluster against the simulation: burst

Workload [burst](../../workloads/burst.json), 30 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and one run of the simulation on the same trace with the same settings. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | Simulation | Cluster minus simulation |
|---|---|---|---|
| Goodput (TTFT within the objective) | 76.4% <sub>(74.7%–79.4%)</sub> | 81.5% <sub>(80.0%–81.7%)</sub> | -5.1 points |
| TTFT p50 (ms) | 244 <sub>(240–260)</sub> | 241 <sub>(236–249)</sub> | +3 |
| TTFT p95 (ms) | 121,236 <sub>(63,796–146,543)</sub> | 44,566 <sub>(43,021–49,684)</sub> | +76,671 |
| TTFT p99 (ms) | 159,481 <sub>(122,955–172,367)</sub> | 58,808 <sub>(58,597–62,832)</sub> | +100,673 |
| Seconds the service was unhealthy | 630 <sub>(510–630)</sub> | 210 <sub>(190–230)</sub> | +420 |
| Replica-seconds (cost) | 36,713 <sub>(34,697–37,795)</sub> | 32,062 <sub>(31,702–32,196)</sub> | +4,651 |
| Peak pods | 32 | 32 | 0 |
| Scale-ups | 10 <sub>(9–11)</sub> | 11 <sub>(9–11)</sub> | -1 |
| Scale-downs | 6 <sub>(4–6)</sub> | 7 | -1 |
| Flaps | 0 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> | -1 |

Requests the cluster did not answer: 31 of 42,581.

### `hpa-queue`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | Simulation | Cluster minus simulation |
|---|---|---|---|
| Goodput (TTFT within the objective) | 70.3% <sub>(64.1%–80.6%)</sub> | 64.3% <sub>(62.3%–73.6%)</sub> | +6.0 points |
| TTFT p50 (ms) | 294 <sub>(236–354)</sub> | 349 <sub>(306–376)</sub> | -55 |
| TTFT p95 (ms) | 88,182 <sub>(60,822–135,626)</sub> | 54,415 <sub>(48,625–57,560)</sub> | +33,767 |
| TTFT p99 (ms) | 141,153 <sub>(79,754–271,153)</sub> | 55,577 <sub>(54,293–68,072)</sub> | +85,575 |
| Seconds the service was unhealthy | 600 <sub>(580–610)</sub> | 370 <sub>(330–420)</sub> | +230 |
| Replica-seconds (cost) | 39,038 <sub>(37,623–42,609)</sub> | 31,860 <sub>(29,952–33,902)</sub> | +7,178 |
| Peak pods | 32 | 32 | 0 |
| Scale-ups | 14 <sub>(14–15)</sub> | 14 <sub>(13–14)</sub> | 0 |
| Scale-downs | 4 <sub>(4–5)</sub> | 3 | +1 |
| Flaps | 8 <sub>(7–10)</sub> | 7 <sub>(5–10)</sub> | +1 |

Requests the cluster did not answer: 64 of 42,581.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | Simulation | Cluster minus simulation |
|---|---|---|---|
| Goodput (TTFT within the objective) | 40.9% <sub>(38.4%–43.3%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | -31.5 points |
| TTFT p50 (ms) | 7,712 <sub>(6,641–12,068)</sub> | 276 <sub>(276–298)</sub> | +7,435 |
| TTFT p95 (ms) | 165,317 <sub>(145,420–202,576)</sub> | 42,736 <sub>(37,689–46,900)</sub> | +122,581 |
| TTFT p99 (ms) | 196,320 <sub>(168,843–245,266)</sub> | 72,059 <sub>(60,916–76,360)</sub> | +124,261 |
| Seconds the service was unhealthy | 970 <sub>(960–990)</sub> | 280 <sub>(270–330)</sub> | +690 |
| Replica-seconds (cost) | 23,028 <sub>(22,726–23,394)</sub> | 28,037 <sub>(27,533–29,613)</sub> | -5,009 |
| Peak pods | 26 <sub>(26–28)</sub> | 32 | -6 |
| Scale-ups | 15 <sub>(13–18)</sub> | 9 <sub>(9–11)</sub> | +6 |
| Scale-downs | 7 <sub>(6–8)</sub> | 6 <sub>(5–6)</sub> | +1 |
| Flaps | 1 <sub>(0–2)</sub> | 0 | +1 |

Requests the cluster did not answer: 5 of 42,581.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | Simulation | Cluster minus simulation |
|---|---|---|---|
| Goodput (TTFT within the objective) | 97.7% <sub>(97.3%–98.1%)</sub> | 100.0% | -2.3 points |
| TTFT p50 (ms) | 188 <sub>(185–192)</sub> | 190 <sub>(185–191)</sub> | -3 |
| TTFT p95 (ms) | 1,038 <sub>(956–1,083)</sub> | 642 <sub>(623–644)</sub> | +396 |
| TTFT p99 (ms) | 3,430 <sub>(2,918–4,243)</sub> | 1,036 <sub>(1,020–1,077)</sub> | +2,395 |
| Seconds the service was unhealthy | 30 <sub>(20–50)</sub> | 0 | +30 |
| Replica-seconds (cost) | 43,200 | 43,200 | 0 |
| Peak pods | 24 | 24 | 0 |
| Scale-ups | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 42,581.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, simulation | TTFT p95 (ms), cluster | TTFT p95 (ms), simulation | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 74.7% | 80.0% | 146,543 | 43,021 | 32 | 32 |
| `hpa-concurrency` | 2 | 79.4% | 81.7% | 63,796 | 44,566 | 32 | 32 |
| `hpa-concurrency` | 3 | 76.4% | 81.5% | 121,236 | 49,684 | 32 | 32 |
| `hpa-queue` | 1 | 80.6% | 62.3% | 135,626 | 54,415 | 32 | 32 |
| `hpa-queue` | 2 | 64.1% | 73.6% | 60,822 | 48,625 | 32 | 32 |
| `hpa-queue` | 3 | 70.3% | 64.3% | 88,182 | 57,560 | 32 | 32 |
| `hpa-utilization` | 1 | 40.9% | 70.6% | 202,576 | 46,900 | 26 | 32 |
| `hpa-utilization` | 2 | 38.4% | 72.3% | 145,420 | 37,689 | 28 | 32 |
| `hpa-utilization` | 3 | 43.3% | 72.5% | 165,317 | 42,736 | 26 | 32 |
| `static-24` | 1 | 97.7% | 100.0% | 1,038 | 642 | 24 | 24 |
| `static-24` | 2 | 97.3% | 100.0% | 1,083 | 644 | 24 | 24 |
| `static-24` | 3 | 98.1% | 100.0% | 956 | 623 | 24 | 24 |
