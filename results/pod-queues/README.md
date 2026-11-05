# The seven datasets again, with a queue per pod

Every dataset in [`results/`](../) was run with one shared queue: a request starts on the least-loaded ready pod with a
free slot, and a pod added later takes the work that is already waiting. The cluster did not behave like that
([the comparison](../cluster/README.md)): behind a Kubernetes Service each request is sent to a pod when it arrives and
waits there. This directory is the same seven datasets, the same policies, the same eight seeds, run with
`--route pod` (`make results-pod-queues`), to see which findings depend on the shared queue.

Each cell below is the median of eight runs. "One queue" is the committed dataset; "queue per pod" is this directory.

| Question | Policy | Goodput, one queue | Goodput, queue per pod | Replica-seconds, one queue | Replica-seconds, queue per pod |
|---|---|---|---|---|---|
| Signal | `static-24` | 100.0% | 98.3% | 43,200 | 43,200 |
| Signal | `hpa-concurrency` | 80.3% | 80.1% | 32,053 | 35,475 |
| Signal | `hpa-utilization` | 68.7% | 51.5% | 27,893 | 23,462 |
| Signal | `hpa-queue` | 63.7% | 79.3% | 33,521 | 37,844 |
| Signal | `hpa-rps` | 54.0% | 60.3% | 18,469 | 18,451 |
| 10 s pod startup | `startup-10s` | 87.7% | 87.9% | 29,551 | 32,439 |
| No scale-up limit | `limit-none` | 82.5% | 81.4% | 32,252 | 36,143 |
| At least 12 pods | `min-12` | 93.5% | 86.3% | 33,076 | 36,859 |
| 30 s scale-down window | `conc-down-30` | 64.1% | 69.2% | 18,817 | 26,893 |
| Pods and decisions in 1 s | `instant` | 100.0% | 95.8% | 26,933 | 28,520 |

## What holds and what does not

**Holds.**

- No HPA signal holds the 2 second objective. The best serves about 80% of requests in time in both models.
- Pod startup is the biggest lever. Pods that start in 10 s instead of 45 buy 7.4 points of goodput with one queue and
  7.8 with a queue per pod, in all eight runs of each. Lifting the scale-up limit buys 2.2 and 1.2.
- Requests in the system still beat slot utilization and request rate in all eight runs.

**Changes.**

- **Requests in the system against queue depth is no longer clear.** With one queue it won all eight runs; with a queue
  per pod it wins five of eight, 80.1% against 79.3%, at 35,475 replica-seconds against 37,844.
- **The autoscaler costs 82% of the static pool, not 74%.**
- **Standing headroom is a weaker lever.** At least 12 pods lifts goodput by 6.1 points for 3.9% more replica-seconds,
  where with one queue it lifted it by 13.2 points for 3.2%.
- **A shorter scale-down window saves less.** A 30 s window cuts cost by 24%, not 41%, and goodput falls from 80.1% to
  69.2%.

**Fails.** One queue says that pods starting in one second with a decision every second serve every request. With a
queue per pod they serve 95.8%, and even the static pool of 24 serves 98.3%: a request sent to a pod that happens to be
busy waits there while others idle. That is a property of per-pod queueing, not of the autoscaler, so a deployment that
needs every request in time needs a router that sees load (the [routing benchmark](https://github.com/sunilmehta-si/k8s-inference-routing-benchmark)).

## Which model is right

Neither is the cluster. On the cluster's twelve runs the queue per pod is closer than the shared queue on the 95th-percentile first token for three of
four policies and ranks the signals as the cluster does, and it overshoots for `hpa-queue`. The shared queue is the
better model of a router that sees load; the queue per pod is the better model of a plain Service. Read the committed
datasets as what autoscaling can do with a good router, and these as what it does behind a Service.
