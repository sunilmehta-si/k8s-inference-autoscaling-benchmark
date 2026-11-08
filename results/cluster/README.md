## The cluster against the simulation: burst

Workload [burst](../../workloads/burst.json), 30 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 76.4% <sub>(74.7%–79.4%)</sub> | 81.5% <sub>(80.0%–81.7%)</sub> | 81.0% <sub>(78.7%–81.4%)</sub> | 75.1% <sub>(74.7%–75.4%)</sub> | 77.4% <sub>(77.2%–78.5%)</sub> | -5.1 points | -4.6 points | +1.3 points | -1.0 points |
| TTFT p50 (ms) | 244 <sub>(240–260)</sub> | 241 <sub>(236–249)</sub> | 248 <sub>(240–261)</sub> | 266 <sub>(263–274)</sub> | 258 <sub>(250–263)</sub> | +3 | -4 | -22 | -15 |
| TTFT p95 (ms) | 121,236 <sub>(63,796–146,543)</sub> | 44,566 <sub>(43,021–49,684)</sub> | 84,696 <sub>(57,884–85,692)</sub> | 121,131 <sub>(71,253–128,059)</sub> | 105,705 <sub>(82,313–105,893)</sub> | +76,671 | +36,540 | +105 | +15,531 |
| TTFT p99 (ms) | 159,481 <sub>(122,955–172,367)</sub> | 58,808 <sub>(58,597–62,832)</sub> | 118,100 <sub>(115,964–153,440)</sub> | 154,471 <sub>(117,833–155,361)</sub> | 151,807 <sub>(132,029–167,142)</sub> | +100,673 | +41,381 | +5,010 | +7,673 |
| Seconds the service was unhealthy | 630 <sub>(510–630)</sub> | 210 <sub>(190–230)</sub> | 450 <sub>(410–530)</sub> | 600 <sub>(510–650)</sub> | 540 <sub>(500–550)</sub> | +420 | +180 | +30 | +90 |
| Replica-seconds (cost) | 36,713 <sub>(34,697–37,795)</sub> | 32,062 <sub>(31,702–32,196)</sub> | 35,126 <sub>(34,442–35,755)</sub> | 37,028 <sub>(35,178–37,396)</sub> | 36,263 <sub>(36,042–36,412)</sub> | +4,651 | +1,587 | -315 | +450 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 10 <sub>(9–11)</sub> | 11 <sub>(9–11)</sub> | 9 <sub>(9–12)</sub> | 9 <sub>(8–11)</sub> | 10 <sub>(9–10)</sub> | -1 | +1 | +1 | 0 |
| Scale-downs | 6 <sub>(4–6)</sub> | 7 | 8 <sub>(6–9)</sub> | 6 <sub>(6–7)</sub> | 5 <sub>(5–9)</sub> | -1 | -2 | 0 | +1 |
| Flaps | 0 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(0–1)</sub> | 0 | 0 | -1 | -1 | 0 | 0 |

Requests the cluster did not answer: 31 of 42,581.

### `hpa-queue`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 70.3% <sub>(64.1%–80.6%)</sub> | 64.3% <sub>(62.3%–73.6%)</sub> | 79.9% <sub>(75.1%–81.5%)</sub> | 73.5% <sub>(70.6%–82.9%)</sub> | 71.7% <sub>(66.3%–80.3%)</sub> | +6.0 points | -9.6 points | -3.2 points | -1.4 points |
| TTFT p50 (ms) | 294 <sub>(236–354)</sub> | 349 <sub>(306–376)</sub> | 247 <sub>(239–267)</sub> | 273 <sub>(248–297)</sub> | 300 <sub>(247–338)</sub> | -55 | +47 | +21 | -6 |
| TTFT p95 (ms) | 88,182 <sub>(60,822–135,626)</sub> | 54,415 <sub>(48,625–57,560)</sub> | 115,062 <sub>(105,495–126,675)</sub> | 76,539 <sub>(18,647–229,095)</sub> | 161,121 <sub>(119,248–175,066)</sub> | +33,767 | -26,880 | +11,643 | -72,939 |
| TTFT p99 (ms) | 141,153 <sub>(79,754–271,153)</sub> | 55,577 <sub>(54,293–68,072)</sub> | 246,769 <sub>(176,484–264,245)</sub> | 150,966 <sub>(142,577–274,218)</sub> | 289,846 <sub>(254,996–305,246)</sub> | +85,575 | -105,616 | -9,813 | -148,694 |
| Seconds the service was unhealthy | 600 <sub>(580–610)</sub> | 370 <sub>(330–420)</sub> | 510 <sub>(510–690)</sub> | 610 <sub>(450–780)</sub> | 530 <sub>(470–630)</sub> | +230 | +90 | -10 | +70 |
| Replica-seconds (cost) | 39,038 <sub>(37,623–42,609)</sub> | 31,860 <sub>(29,952–33,902)</sub> | 39,025 <sub>(37,502–44,854)</sub> | 38,879 <sub>(34,792–47,703)</sub> | 41,347 <sub>(37,261–42,736)</sub> | +7,178 | +13 | +159 | -2,309 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 14 <sub>(14–15)</sub> | 14 <sub>(13–14)</sub> | 12 <sub>(11–15)</sub> | 12 <sub>(11–13)</sub> | 13 <sub>(12–16)</sub> | 0 | +2 | +2 | +1 |
| Scale-downs | 4 <sub>(4–5)</sub> | 3 | 4 <sub>(3–5)</sub> | 4 <sub>(3–4)</sub> | 3 <sub>(2–4)</sub> | +1 | 0 | 0 | +1 |
| Flaps | 8 <sub>(7–10)</sub> | 7 <sub>(5–10)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(5–8)</sub> | 8 <sub>(6–10)</sub> | +1 | +1 | +1 | 0 |

Requests the cluster did not answer: 64 of 42,581.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 40.9% <sub>(38.4%–43.3%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–57.1%)</sub> | 38.3% <sub>(36.9%–42.9%)</sub> | 46.4% <sub>(41.4%–49.2%)</sub> | -31.5 points | -15.4 points | +2.6 points | -5.5 points |
| TTFT p50 (ms) | 7,712 <sub>(6,641–12,068)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(586–2,174)</sub> | 12,719 <sub>(5,984–17,260)</sub> | 4,250 <sub>(2,350–9,155)</sub> | +7,435 | +7,079 | -5,007 | +3,461 |
| TTFT p95 (ms) | 165,317 <sub>(145,420–202,576)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | 131,347 <sub>(124,645–134,152)</sub> | 140,077 <sub>(101,840–149,725)</sub> | +122,581 | +83,874 | +33,971 | +25,240 |
| TTFT p99 (ms) | 196,320 <sub>(168,843–245,266)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | 147,895 <sub>(137,607–163,297)</sub> | 166,528 <sub>(113,189–170,904)</sub> | +124,261 | +80,096 | +48,424 | +29,792 |
| Seconds the service was unhealthy | 970 <sub>(960–990)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(690–880)</sub> | 940 <sub>(910–960)</sub> | 890 <sub>(760–920)</sub> | +690 | +240 | +30 | +80 |
| Replica-seconds (cost) | 23,028 <sub>(22,726–23,394)</sub> | 28,037 <sub>(27,533–29,613)</sub> | 23,419 <sub>(22,926–24,022)</sub> | 21,887 <sub>(20,852–23,220)</sub> | 22,924 <sub>(22,798–24,214)</sub> | -5,009 | -391 | +1,141 | +104 |
| Peak pods | 26 <sub>(26–28)</sub> | 32 | 26 <sub>(23–27)</sub> | 23 <sub>(21–25)</sub> | 25 <sub>(24–27)</sub> | -6 | 0 | +3 | +1 |
| Scale-ups | 15 <sub>(13–18)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | 11 <sub>(9–12)</sub> | 14 <sub>(12–15)</sub> | +6 | +2 | +4 | +1 |
| Scale-downs | 7 <sub>(6–8)</sub> | 6 <sub>(5–6)</sub> | 5 <sub>(5–7)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(6–8)</sub> | +1 | +2 | 0 | 0 |
| Flaps | 1 <sub>(0–2)</sub> | 0 | 0 | 0 | 0 | +1 | +1 | +1 | +1 |

Requests the cluster did not answer: 5 of 42,581.

### `static-24`

3 seeds (1, 2, 3). Pods start in 45 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 97.7% <sub>(97.3%–98.1%)</sub> | 100.0% | 98.4% <sub>(97.9%–98.6%)</sub> | 98.4% <sub>(97.9%–98.6%)</sub> | 98.4% <sub>(97.9%–98.6%)</sub> | -2.3 points | -0.7 points | -0.7 points | -0.7 points |
| TTFT p50 (ms) | 188 <sub>(185–192)</sub> | 190 <sub>(185–191)</sub> | 201 <sub>(199–203)</sub> | 201 <sub>(199–203)</sub> | 201 <sub>(199–203)</sub> | -3 | -13 | -13 | -13 |
| TTFT p95 (ms) | 1,038 <sub>(956–1,083)</sub> | 642 <sub>(623–644)</sub> | 914 <sub>(881–933)</sub> | 914 <sub>(881–933)</sub> | 914 <sub>(881–933)</sub> | +396 | +124 | +124 | +124 |
| TTFT p99 (ms) | 3,430 <sub>(2,918–4,243)</sub> | 1,036 <sub>(1,020–1,077)</sub> | 2,886 <sub>(2,533–3,715)</sub> | 2,886 <sub>(2,533–3,715)</sub> | 2,886 <sub>(2,533–3,715)</sub> | +2,395 | +544 | +544 | +544 |
| Seconds the service was unhealthy | 30 <sub>(20–50)</sub> | 0 | 30 <sub>(20–30)</sub> | 30 <sub>(20–30)</sub> | 30 <sub>(20–30)</sub> | +30 | 0 | 0 | 0 |
| Replica-seconds (cost) | 43,200 | 43,200 | 43,200 | 43,200 | 43,200 | 0 | 0 | 0 | 0 |
| Peak pods | 24 | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 0 |
| Scale-ups | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Scale-downs | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Flaps | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 0 of 42,581.

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 74.7% | 80.0% | 78.7% | 74.7% | 77.2% | 146,543 | 43,021 | 84,696 | 121,131 | 105,705 | 32 | 32 |
| `hpa-concurrency` | 2 | 79.4% | 81.7% | 81.0% | 75.4% | 77.4% | 63,796 | 44,566 | 57,884 | 71,253 | 82,313 | 32 | 32 |
| `hpa-concurrency` | 3 | 76.4% | 81.5% | 81.4% | 75.1% | 78.5% | 121,236 | 49,684 | 85,692 | 128,059 | 105,893 | 32 | 32 |
| `hpa-queue` | 1 | 80.6% | 62.3% | 79.9% | 82.9% | 80.3% | 135,626 | 54,415 | 115,062 | 18,647 | 119,248 | 32 | 32 |
| `hpa-queue` | 2 | 64.1% | 73.6% | 75.1% | 73.5% | 66.3% | 60,822 | 48,625 | 126,675 | 229,095 | 175,066 | 32 | 32 |
| `hpa-queue` | 3 | 70.3% | 64.3% | 81.5% | 70.6% | 71.7% | 88,182 | 57,560 | 105,495 | 76,539 | 161,121 | 32 | 32 |
| `hpa-utilization` | 1 | 40.9% | 70.6% | 56.2% | 42.9% | 46.4% | 202,576 | 46,900 | 71,830 | 124,645 | 149,725 | 26 | 32 |
| `hpa-utilization` | 2 | 38.4% | 72.3% | 49.7% | 38.3% | 41.4% | 145,420 | 37,689 | 108,516 | 131,347 | 140,077 | 28 | 32 |
| `hpa-utilization` | 3 | 43.3% | 72.5% | 57.1% | 36.9% | 49.2% | 165,317 | 42,736 | 81,443 | 134,152 | 101,840 | 26 | 32 |
| `static-24` | 1 | 97.7% | 100.0% | 97.9% | 97.9% | 97.9% | 1,038 | 642 | 933 | 933 | 933 | 24 | 24 |
| `static-24` | 2 | 97.3% | 100.0% | 98.4% | 98.4% | 98.4% | 1,083 | 644 | 914 | 914 | 914 | 24 | 24 |
| `static-24` | 3 | 98.1% | 100.0% | 98.6% | 98.6% | 98.6% | 956 | 623 | 881 | 881 | 881 | 24 | 24 |
