## KEDA beside the HPA on the cluster: burst

Workload [burst](../../workloads/burst.json), 30 minutes, objective a first token within 2 s. Each seed is one run on a kind cluster (the real Horizontal Pod Autoscaler, Prometheus and prometheus-adapter, simulated vLLM pods) and four runs of the simulation on the same trace with the same settings: one with a single shared queue; one with a queue per pod, each request sent to a random ready pod when it arrives, as behind a Kubernetes Service; one with a queue per pod and the autoscaler acting on the signal as it was 30 s earlier, as the cluster's Prometheus scrape and rule intervals make it; and one with a queue per pod and that pipeline piece by piece: each pod scraped every 15 s at its own offset, a rule evaluated every 15 s at its own offset, and the autoscaler reading the latest evaluation. Each cell is the median over the seeds, with the lowest and highest in brackets. A `keda-` run has KEDA in place of prometheus-adapter: KEDA's operator sums the recorded series in Prometheus, and the autoscaler it creates reads that sum as an external metric, averaged over every pod the Deployment has; its simulation is the same controller reading that metric.

### `hpa-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 76.3% <sub>(75.9%–78.1%)</sub> | 81.5% <sub>(80.0%–81.7%)</sub> | 81.0% <sub>(78.7%–81.4%)</sub> | 75.1% <sub>(74.7%–75.4%)</sub> | 77.4% <sub>(77.2%–78.5%)</sub> | -5.2 points | -4.7 points | +1.2 points | -1.1 points |
| TTFT p50 (ms) | 254 <sub>(240–256)</sub> | 241 <sub>(236–249)</sub> | 248 <sub>(240–261)</sub> | 266 <sub>(263–274)</sub> | 258 <sub>(250–263)</sub> | +13 | +6 | -12 | -5 |
| TTFT p95 (ms) | 107,155 <sub>(88,264–136,018)</sub> | 44,566 <sub>(43,021–49,684)</sub> | 84,696 <sub>(57,884–85,692)</sub> | 121,131 <sub>(71,253–128,059)</sub> | 105,705 <sub>(82,313–105,893)</sub> | +62,590 | +22,460 | -13,976 | +1,450 |
| TTFT p99 (ms) | 126,388 <sub>(121,803–168,310)</sub> | 58,808 <sub>(58,597–62,832)</sub> | 118,100 <sub>(115,964–153,440)</sub> | 154,471 <sub>(117,833–155,361)</sub> | 151,807 <sub>(132,029–167,142)</sub> | +67,580 | +8,288 | -28,082 | -25,419 |
| Seconds the service was unhealthy | 590 <sub>(540–630)</sub> | 210 <sub>(190–230)</sub> | 450 <sub>(410–530)</sub> | 600 <sub>(510–650)</sub> | 540 <sub>(500–550)</sub> | +380 | +140 | -10 | +50 |
| Replica-seconds (cost) | 36,539 <sub>(35,693–37,210)</sub> | 32,062 <sub>(31,702–32,196)</sub> | 35,126 <sub>(34,442–35,755)</sub> | 37,028 <sub>(35,178–37,396)</sub> | 36,263 <sub>(36,042–36,412)</sub> | +4,477 | +1,414 | -489 | +276 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 10 <sub>(9–13)</sub> | 11 <sub>(9–11)</sub> | 9 <sub>(9–12)</sub> | 9 <sub>(8–11)</sub> | 10 <sub>(9–10)</sub> | -1 | +1 | +1 | 0 |
| Scale-downs | 6 <sub>(5–7)</sub> | 7 | 8 <sub>(6–9)</sub> | 6 <sub>(6–7)</sub> | 5 <sub>(5–9)</sub> | -1 | -2 | 0 | +1 |
| Flaps | 2 <sub>(1–3)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(0–1)</sub> | 0 | 0 | +1 | +1 | +2 | +2 |

Requests the cluster did not answer: 38 of 42,581.

### `hpa-queue`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 77.9% <sub>(75.7%–80.2%)</sub> | 64.3% <sub>(62.3%–73.6%)</sub> | 79.9% <sub>(75.1%–81.5%)</sub> | 73.5% <sub>(70.6%–82.9%)</sub> | 71.7% <sub>(66.3%–80.3%)</sub> | +13.6 points | -2.1 points | +4.3 points | +6.2 points |
| TTFT p50 (ms) | 248 <sub>(228–268)</sub> | 349 <sub>(306–376)</sub> | 247 <sub>(239–267)</sub> | 273 <sub>(248–297)</sub> | 300 <sub>(247–338)</sub> | -101 | +1 | -26 | -53 |
| TTFT p95 (ms) | 138,784 <sub>(125,665–197,313)</sub> | 54,415 <sub>(48,625–57,560)</sub> | 115,062 <sub>(105,495–126,675)</sub> | 76,539 <sub>(18,647–229,095)</sub> | 161,121 <sub>(119,248–175,066)</sub> | +84,369 | +23,722 | +62,245 | -22,337 |
| TTFT p99 (ms) | 268,620 <sub>(259,540–322,161)</sub> | 55,577 <sub>(54,293–68,072)</sub> | 246,769 <sub>(176,484–264,245)</sub> | 150,966 <sub>(142,577–274,218)</sub> | 289,846 <sub>(254,996–305,246)</sub> | +213,043 | +21,851 | +117,654 | -21,226 |
| Seconds the service was unhealthy | 560 <sub>(540–610)</sub> | 370 <sub>(330–420)</sub> | 510 <sub>(510–690)</sub> | 610 <sub>(450–780)</sub> | 530 <sub>(470–630)</sub> | +190 | +50 | -50 | +30 |
| Replica-seconds (cost) | 38,765 <sub>(34,549–44,268)</sub> | 31,860 <sub>(29,952–33,902)</sub> | 39,025 <sub>(37,502–44,854)</sub> | 38,879 <sub>(34,792–47,703)</sub> | 41,347 <sub>(37,261–42,736)</sub> | +6,904 | -261 | -115 | -2,582 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 13 <sub>(11–13)</sub> | 14 <sub>(13–14)</sub> | 12 <sub>(11–15)</sub> | 12 <sub>(11–13)</sub> | 13 <sub>(12–16)</sub> | -1 | +1 | +1 | 0 |
| Scale-downs | 5 <sub>(4–6)</sub> | 3 | 4 <sub>(3–5)</sub> | 4 <sub>(3–4)</sub> | 3 <sub>(2–4)</sub> | +2 | +1 | +1 | +2 |
| Flaps | 7 <sub>(7–8)</sub> | 7 <sub>(5–10)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(5–8)</sub> | 8 <sub>(6–10)</sub> | 0 | 0 | 0 | -1 |

Requests the cluster did not answer: 44 of 42,581.

### `hpa-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 40.6% <sub>(39.2%–43.9%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–57.1%)</sub> | 38.3% <sub>(36.9%–42.9%)</sub> | 46.4% <sub>(41.4%–49.2%)</sub> | -31.7 points | -15.6 points | +2.4 points | -5.7 points |
| TTFT p50 (ms) | 12,668 <sub>(6,244–12,876)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(586–2,174)</sub> | 12,719 <sub>(5,984–17,260)</sub> | 4,250 <sub>(2,350–9,155)</sub> | +12,391 | +12,035 | -51 | +8,418 |
| TTFT p95 (ms) | 148,063 <sub>(104,697–180,192)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | 131,347 <sub>(124,645–134,152)</sub> | 140,077 <sub>(101,840–149,725)</sub> | +105,327 | +66,620 | +16,717 | +7,986 |
| TTFT p99 (ms) | 165,541 <sub>(120,970–200,586)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | 147,895 <sub>(137,607–163,297)</sub> | 166,528 <sub>(113,189–170,904)</sub> | +93,482 | +49,318 | +17,645 | -987 |
| Seconds the service was unhealthy | 1,040 <sub>(880–1,080)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(690–880)</sub> | 940 <sub>(910–960)</sub> | 890 <sub>(760–920)</sub> | +760 | +310 | +100 | +150 |
| Replica-seconds (cost) | 22,500 <sub>(21,273–22,753)</sub> | 28,037 <sub>(27,533–29,613)</sub> | 23,419 <sub>(22,926–24,022)</sub> | 21,887 <sub>(20,852–23,220)</sub> | 22,924 <sub>(22,798–24,214)</sub> | -5,537 | -919 | +612 | -424 |
| Peak pods | 25 <sub>(25–27)</sub> | 32 | 26 <sub>(23–27)</sub> | 23 <sub>(21–25)</sub> | 25 <sub>(24–27)</sub> | -7 | -1 | +2 | 0 |
| Scale-ups | 15 <sub>(14–16)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | 11 <sub>(9–12)</sub> | 14 <sub>(12–15)</sub> | +6 | +2 | +4 | +1 |
| Scale-downs | 7 <sub>(5–8)</sub> | 6 <sub>(5–6)</sub> | 5 <sub>(5–7)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(6–8)</sub> | +1 | +2 | 0 | 0 |
| Flaps | 1 <sub>(0–1)</sub> | 0 | 0 | 0 | 0 | +1 | +1 | +1 | +1 |

Requests the cluster did not answer: 4 of 42,581.

### `keda-concurrency`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 77.3% <sub>(75.8%–77.4%)</sub> | 81.5% <sub>(80.0%–81.7%)</sub> | 81.0% <sub>(78.7%–81.4%)</sub> | 75.1% <sub>(74.7%–75.4%)</sub> | 77.4% <sub>(77.2%–78.5%)</sub> | -4.2 points | -3.7 points | +2.2 points | -0.1 points |
| TTFT p50 (ms) | 249 <sub>(240–264)</sub> | 241 <sub>(236–249)</sub> | 248 <sub>(240–261)</sub> | 265 <sub>(263–274)</sub> | 258 <sub>(250–263)</sub> | +8 | +1 | -17 | -10 |
| TTFT p95 (ms) | 106,326 <sub>(76,084–150,056)</sub> | 44,566 <sub>(43,021–49,684)</sub> | 84,696 <sub>(57,884–85,692)</sub> | 121,131 <sub>(71,253–128,059)</sub> | 105,705 <sub>(82,313–105,893)</sub> | +61,761 | +21,630 | -14,805 | +621 |
| TTFT p99 (ms) | 128,828 <sub>(119,516–181,245)</sub> | 58,808 <sub>(58,597–62,832)</sub> | 118,100 <sub>(115,964–153,440)</sub> | 154,471 <sub>(117,833–155,361)</sub> | 151,807 <sub>(132,029–167,142)</sub> | +70,020 | +10,728 | -25,642 | -22,979 |
| Seconds the service was unhealthy | 620 <sub>(500–670)</sub> | 210 <sub>(190–230)</sub> | 450 <sub>(410–530)</sub> | 600 <sub>(510–650)</sub> | 540 <sub>(500–550)</sub> | +410 | +170 | +20 | +80 |
| Replica-seconds (cost) | 36,730 <sub>(35,026–38,216)</sub> | 32,062 <sub>(31,702–32,196)</sub> | 35,126 <sub>(34,442–35,755)</sub> | 37,028 <sub>(35,103–37,396)</sub> | 36,263 <sub>(36,042–36,412)</sub> | +4,668 | +1,604 | -298 | +467 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 9 <sub>(8–10)</sub> | 11 <sub>(9–11)</sub> | 9 <sub>(9–12)</sub> | 9 <sub>(8–11)</sub> | 10 <sub>(9–10)</sub> | -2 | 0 | 0 | -1 |
| Scale-downs | 6 <sub>(4–9)</sub> | 7 | 8 <sub>(6–9)</sub> | 6 <sub>(6–7)</sub> | 5 <sub>(5–9)</sub> | -1 | -2 | 0 | +1 |
| Flaps | 0 <sub>(0–2)</sub> | 1 <sub>(1–2)</sub> | 1 <sub>(0–1)</sub> | 0 | 0 | -1 | -1 | 0 | 0 |

Requests the cluster did not answer: 52 of 42,581.

### `keda-queue`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 79.7% <sub>(68.8%–81.7%)</sub> | 64.3% <sub>(62.3%–73.6%)</sub> | 79.9% <sub>(75.1%–81.5%)</sub> | 73.2% <sub>(70.6%–81.7%)</sub> | 72.7% <sub>(66.3%–80.3%)</sub> | +15.4 points | -0.2 points | +6.5 points | +7.0 points |
| TTFT p50 (ms) | 230 <sub>(229–333)</sub> | 349 <sub>(306–376)</sub> | 247 <sub>(239–267)</sub> | 276 <sub>(251–297)</sub> | 289 <sub>(247–338)</sub> | -118 | -16 | -45 | -59 |
| TTFT p95 (ms) | 127,589 <sub>(66,088–217,565)</sub> | 54,415 <sub>(48,625–57,560)</sub> | 115,062 <sub>(105,495–126,675)</sub> | 76,539 <sub>(26,629–229,890)</sub> | 143,863 <sub>(119,248–175,066)</sub> | +73,175 | +12,528 | +51,051 | -16,274 |
| TTFT p99 (ms) | 272,968 <sub>(201,053–339,899)</sub> | 55,577 <sub>(54,293–68,072)</sub> | 246,769 <sub>(176,484–264,245)</sub> | 154,484 <sub>(150,966–277,548)</sub> | 299,535 <sub>(254,996–305,246)</sub> | +217,391 | +26,200 | +118,485 | -26,566 |
| Seconds the service was unhealthy | 600 <sub>(540–620)</sub> | 370 <sub>(330–420)</sub> | 510 <sub>(510–690)</sub> | 610 <sub>(490–830)</sub> | 510 <sub>(470–630)</sub> | +230 | +90 | -10 | +90 |
| Replica-seconds (cost) | 39,361 <sub>(38,589–40,091)</sub> | 31,860 <sub>(29,952–33,834)</sub> | 39,025 <sub>(37,502–44,854)</sub> | 38,918 <sub>(34,792–47,265)</sub> | 41,347 <sub>(36,756–42,736)</sub> | +7,501 | +336 | +442 | -1,986 |
| Peak pods | 32 | 32 | 32 | 32 | 32 | 0 | 0 | 0 | 0 |
| Scale-ups | 12 <sub>(11–14)</sub> | 14 <sub>(13–14)</sub> | 12 <sub>(11–15)</sub> | 12 <sub>(11–13)</sub> | 14 <sub>(12–16)</sub> | -2 | 0 | 0 | -2 |
| Scale-downs | 6 <sub>(4–6)</sub> | 3 <sub>(3–4)</sub> | 4 <sub>(3–5)</sub> | 5 <sub>(3–5)</sub> | 4 <sub>(3–5)</sub> | +3 | +2 | +1 | +2 |
| Flaps | 7 | 7 <sub>(5–10)</sub> | 7 <sub>(6–9)</sub> | 7 <sub>(5–8)</sub> | 9 <sub>(8–10)</sub> | 0 | 0 | 0 | -2 |

Requests the cluster did not answer: 69 of 42,581.

### `keda-utilization`

3 seeds (1, 2, 3). Pods start in 45 s, scale-down window 300 s.

| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |
|---|---|---|---|---|---|---|---|---|---|
| Goodput (TTFT within the objective) | 48.2% <sub>(47.1%–49.2%)</sub> | 72.3% <sub>(70.6%–72.5%)</sub> | 56.2% <sub>(49.7%–56.7%)</sub> | 38.3% <sub>(36.9%–42.9%)</sub> | 46.4% <sub>(41.4%–48.5%)</sub> | -24.2 points | -8.1 points | +9.9 points | +1.8 points |
| TTFT p50 (ms) | 2,745 <sub>(2,396–3,403)</sub> | 276 <sub>(276–298)</sub> | 633 <sub>(618–2,174)</sub> | 12,719 <sub>(5,984–17,260)</sub> | 4,250 <sub>(3,077–9,155)</sub> | +2,469 | +2,113 | -9,974 | -1,505 |
| TTFT p95 (ms) | 139,868 <sub>(98,384–183,047)</sub> | 42,736 <sub>(37,689–46,900)</sub> | 81,443 <sub>(71,830–108,516)</sub> | 131,347 <sub>(124,645–134,152)</sub> | 140,077 <sub>(101,924–149,725)</sub> | +97,132 | +58,425 | +8,522 | -209 |
| TTFT p99 (ms) | 156,371 <sub>(117,862–219,107)</sub> | 72,059 <sub>(60,916–76,360)</sub> | 116,223 <sub>(105,555–138,997)</sub> | 147,895 <sub>(137,607–163,297)</sub> | 166,528 <sub>(113,486–170,904)</sub> | +84,312 | +40,148 | +8,475 | -10,157 |
| Seconds the service was unhealthy | 860 <sub>(780–860)</sub> | 280 <sub>(270–330)</sub> | 730 <sub>(700–880)</sub> | 940 <sub>(910–960)</sub> | 890 <sub>(790–920)</sub> | +580 | +130 | -80 | -30 |
| Replica-seconds (cost) | 23,975 <sub>(23,027–24,446)</sub> | 28,037 <sub>(27,533–29,538)</sub> | 23,419 <sub>(22,926–24,022)</sub> | 21,887 <sub>(20,852–23,220)</sub> | 22,924 <sub>(22,798–23,944)</sub> | -4,062 | +557 | +2,088 | +1,051 |
| Peak pods | 26 <sub>(24–28)</sub> | 32 | 26 <sub>(23–27)</sub> | 23 <sub>(21–25)</sub> | 25 <sub>(24–27)</sub> | -6 | 0 | +3 | +1 |
| Scale-ups | 13 <sub>(13–14)</sub> | 9 <sub>(9–11)</sub> | 13 <sub>(11–14)</sub> | 11 <sub>(9–12)</sub> | 14 <sub>(12–15)</sub> | +4 | 0 | +2 | -1 |
| Scale-downs | 6 <sub>(6–10)</sub> | 6 | 5 <sub>(5–7)</sub> | 7 <sub>(6–9)</sub> | 8 <sub>(6–8)</sub> | 0 | +1 | -1 | -2 |
| Flaps | 0 <sub>(0–1)</sub> | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Requests the cluster did not answer: 10 of 42,581.

### KEDA against the HPA, on the cluster

Each signal run both ways on the same seeds: the HPA reading a pods metric through prometheus-adapter, and the HPA KEDA creates reading the sum over the pods as an external metric. A seed counts as better or worse when its two runs differ at all.

#### concurrency

Seeds 1, 2, 3.

| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 76.3% <sub>(75.9%–78.1%)</sub> | 77.3% <sub>(75.8%–77.4%)</sub> | +1.0 points | KEDA better in 1, worse in 2 of 3 |
| TTFT p50 (ms) | 254 <sub>(240–256)</sub> | 249 <sub>(240–264)</sub> | -5 | KEDA better in 2, worse in 1 of 3 |
| TTFT p95 (ms) | 107,155 <sub>(88,264–136,018)</sub> | 106,326 <sub>(76,084–150,056)</sub> | -829 | KEDA better in 2, worse in 1 of 3 |
| TTFT p99 (ms) | 126,388 <sub>(121,803–168,310)</sub> | 128,828 <sub>(119,516–181,245)</sub> | +2,440 | KEDA better in 1, worse in 2 of 3 |
| Seconds the service was unhealthy | 590 <sub>(540–630)</sub> | 620 <sub>(500–670)</sub> | +30 | KEDA better in 1, worse in 2 of 3 |
| Replica-seconds (cost) | 36,539 <sub>(35,693–37,210)</sub> | 36,730 <sub>(35,026–38,216)</sub> | +191 | KEDA better in 1, worse in 2 of 3 |
| Peak pods | 32 | 32 | 0 | KEDA higher in 0, lower in 0 of 3 |
| Scale-ups | 10 <sub>(9–13)</sub> | 9 <sub>(8–10)</sub> | -1 | KEDA higher in 0, lower in 1 of 3 |
| Scale-downs | 6 <sub>(5–7)</sub> | 6 <sub>(4–9)</sub> | 0 | KEDA higher in 1, lower in 2 of 3 |
| Flaps | 2 <sub>(1–3)</sub> | 0 <sub>(0–2)</sub> | -2 | KEDA higher in 0, lower in 2 of 3 |

#### queue

Seeds 1, 2, 3.

| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 77.9% <sub>(75.7%–80.2%)</sub> | 79.7% <sub>(68.8%–81.7%)</sub> | +1.8 points | KEDA better in 1, worse in 2 of 3 |
| TTFT p50 (ms) | 248 <sub>(228–268)</sub> | 230 <sub>(229–333)</sub> | -17 | KEDA better in 1, worse in 2 of 3 |
| TTFT p95 (ms) | 138,784 <sub>(125,665–197,313)</sub> | 127,589 <sub>(66,088–217,565)</sub> | -11,194 | KEDA better in 2, worse in 1 of 3 |
| TTFT p99 (ms) | 268,620 <sub>(259,540–322,161)</sub> | 272,968 <sub>(201,053–339,899)</sub> | +4,348 | KEDA better in 1, worse in 2 of 3 |
| Seconds the service was unhealthy | 560 <sub>(540–610)</sub> | 600 <sub>(540–620)</sub> | +40 | KEDA better in 2, worse in 1 of 3 |
| Replica-seconds (cost) | 38,765 <sub>(34,549–44,268)</sub> | 39,361 <sub>(38,589–40,091)</sub> | +596 | KEDA better in 1, worse in 2 of 3 |
| Peak pods | 32 | 32 | 0 | KEDA higher in 0, lower in 0 of 3 |
| Scale-ups | 13 <sub>(11–13)</sub> | 12 <sub>(11–14)</sub> | -1 | KEDA higher in 1, lower in 1 of 3 |
| Scale-downs | 5 <sub>(4–6)</sub> | 6 <sub>(4–6)</sub> | +1 | KEDA higher in 1, lower in 0 of 3 |
| Flaps | 7 <sub>(7–8)</sub> | 7 | 0 | KEDA higher in 0, lower in 1 of 3 |

#### utilization

Seeds 1, 2, 3.

| Metric | HPA | KEDA | KEDA minus HPA | Seed by seed |
|---|---|---|---|---|
| Goodput (TTFT within the objective) | 40.6% <sub>(39.2%–43.9%)</sub> | 48.2% <sub>(47.1%–49.2%)</sub> | +7.5 points | KEDA better in 3, worse in 0 of 3 |
| TTFT p50 (ms) | 12,668 <sub>(6,244–12,876)</sub> | 2,745 <sub>(2,396–3,403)</sub> | -9,922 | KEDA better in 3, worse in 0 of 3 |
| TTFT p95 (ms) | 148,063 <sub>(104,697–180,192)</sub> | 139,868 <sub>(98,384–183,047)</sub> | -8,195 | KEDA better in 2, worse in 1 of 3 |
| TTFT p99 (ms) | 165,541 <sub>(120,970–200,586)</sub> | 156,371 <sub>(117,862–219,107)</sub> | -9,170 | KEDA better in 2, worse in 1 of 3 |
| Seconds the service was unhealthy | 1,040 <sub>(880–1,080)</sub> | 860 <sub>(780–860)</sub> | -180 | KEDA better in 3, worse in 0 of 3 |
| Replica-seconds (cost) | 22,500 <sub>(21,273–22,753)</sub> | 23,975 <sub>(23,027–24,446)</sub> | +1,475 | KEDA better in 0, worse in 3 of 3 |
| Peak pods | 25 <sub>(25–27)</sub> | 26 <sub>(24–28)</sub> | +1 | KEDA higher in 2, lower in 1 of 3 |
| Scale-ups | 15 <sub>(14–16)</sub> | 13 <sub>(13–14)</sub> | -2 | KEDA higher in 0, lower in 2 of 3 |
| Scale-downs | 7 <sub>(5–8)</sub> | 6 <sub>(6–10)</sub> | -1 | KEDA higher in 2, lower in 1 of 3 |
| Flaps | 1 <sub>(0–1)</sub> | 0 <sub>(0–1)</sub> | -1 | KEDA higher in 0, lower in 1 of 3 |

### Run by run

| Policy | Seed | Goodput, cluster | Goodput, one queue | Goodput, queue per pod | Goodput, queue per pod, lag | Goodput, queue per pod, scraped | TTFT p95 (ms), cluster | TTFT p95 (ms), one queue | TTFT p95 (ms), queue per pod | TTFT p95 (ms), queue per pod, lag | TTFT p95 (ms), queue per pod, scraped | Pods at peak, cluster | Pods at peak, simulation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hpa-concurrency` | 1 | 75.9% | 80.0% | 78.7% | 74.7% | 77.2% | 107,155 | 43,021 | 84,696 | 121,131 | 105,705 | 32 | 32 |
| `hpa-concurrency` | 2 | 76.3% | 81.7% | 81.0% | 75.4% | 77.4% | 88,264 | 44,566 | 57,884 | 71,253 | 82,313 | 32 | 32 |
| `hpa-concurrency` | 3 | 78.1% | 81.5% | 81.4% | 75.1% | 78.5% | 136,018 | 49,684 | 85,692 | 128,059 | 105,893 | 32 | 32 |
| `hpa-queue` | 1 | 77.9% | 62.3% | 79.9% | 82.9% | 80.3% | 138,784 | 54,415 | 115,062 | 18,647 | 119,248 | 32 | 32 |
| `hpa-queue` | 2 | 75.7% | 73.6% | 75.1% | 73.5% | 66.3% | 197,313 | 48,625 | 126,675 | 229,095 | 175,066 | 32 | 32 |
| `hpa-queue` | 3 | 80.2% | 64.3% | 81.5% | 70.6% | 71.7% | 125,665 | 57,560 | 105,495 | 76,539 | 161,121 | 32 | 32 |
| `hpa-utilization` | 1 | 40.6% | 70.6% | 56.2% | 42.9% | 46.4% | 180,192 | 46,900 | 71,830 | 124,645 | 149,725 | 25 | 32 |
| `hpa-utilization` | 2 | 39.2% | 72.3% | 49.7% | 38.3% | 41.4% | 148,063 | 37,689 | 108,516 | 131,347 | 140,077 | 25 | 32 |
| `hpa-utilization` | 3 | 43.9% | 72.5% | 57.1% | 36.9% | 49.2% | 104,697 | 42,736 | 81,443 | 134,152 | 101,840 | 27 | 32 |
| `keda-concurrency` | 1 | 75.8% | 80.0% | 78.7% | 74.7% | 77.2% | 106,326 | 43,021 | 84,696 | 121,131 | 105,705 | 32 | 32 |
| `keda-concurrency` | 2 | 77.3% | 81.7% | 81.0% | 75.4% | 77.4% | 76,084 | 44,566 | 57,884 | 71,253 | 82,313 | 32 | 32 |
| `keda-concurrency` | 3 | 77.4% | 81.5% | 81.4% | 75.1% | 78.5% | 150,056 | 49,684 | 85,692 | 128,059 | 105,893 | 32 | 32 |
| `keda-queue` | 1 | 81.7% | 62.3% | 79.9% | 81.7% | 80.3% | 127,589 | 54,415 | 115,062 | 26,629 | 119,248 | 32 | 32 |
| `keda-queue` | 2 | 68.8% | 73.6% | 75.1% | 73.2% | 66.3% | 217,565 | 48,625 | 126,675 | 229,890 | 175,066 | 32 | 32 |
| `keda-queue` | 3 | 79.7% | 64.3% | 81.5% | 70.6% | 72.7% | 66,088 | 57,560 | 105,495 | 76,539 | 143,863 | 32 | 32 |
| `keda-utilization` | 1 | 49.2% | 70.6% | 56.2% | 42.9% | 46.4% | 98,384 | 46,900 | 71,830 | 124,645 | 149,725 | 26 | 32 |
| `keda-utilization` | 2 | 47.1% | 72.3% | 49.7% | 38.3% | 41.4% | 139,868 | 37,689 | 108,516 | 131,347 | 140,077 | 24 | 32 |
| `keda-utilization` | 3 | 48.2% | 72.5% | 56.7% | 36.9% | 48.5% | 183,047 | 42,736 | 81,443 | 134,152 | 101,924 | 28 | 32 |
