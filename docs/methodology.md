# Methodology

This benchmark is a model, so the first job of this page is to say what the model is, what it leaves out, and what
that means for how far the results can be trusted.

## The model

**Pods.** A pod serves up to 8 requests at once, the way a vLLM server batches. A request's time depends on its size
and on how many requests share the pod when it starts:

```
prefill  = prompt_tokens / 4000 per second        x (1 + 0.5 x (others on the pod) / 8)
per token = 0.020 s                                x (1 + 0.6 x (others on the pod) / 8)
first token (TTFT) = wait + prefill + one token
last token         = wait + prefill + output_tokens x per token
```

**One queue.** Requests wait in one shared queue and start on the ready pod with the most free slots. This stands in
for a perfect router, so a difference between two runs is the autoscaler's and not the router's. The sibling
[routing benchmark](https://github.com/sunilmehta-si/k8s-inference-routing-benchmark) measures routing.

**Pod lifecycle.** A new pod costs from the moment it is created and serves nothing until `startup` has passed (45 s
unless a spec says otherwise: scheduling, pulling the image, loading the model). Scaling down removes pods that are
still starting first, then the ready pods holding the fewest requests. A removed pod takes no new requests, finishes
the ones it has, and stops costing when it is empty. Nothing is dropped.

**The controller.** Every 15 s, the HPA default, the autoscaler sees the pods and the queue and may change the
count, between 2 and 32 pods unless a spec sets its own fewest. `hpa-*` policies follow the Kubernetes
HorizontalPodAutoscaler's algorithm for a per-pod metric, step by step (see `inference_autoscaling_bench/policies.py`):

1. ratio = (metric summed over the ready pods / ready pods) / target. Within 10% of 1, change nothing.
2. If the ratio is above 1 and some pods are still starting, recompute it counting those pods as using none of the
   metric. If that lands within 10% of 1 or on the other side of 1, change nothing; otherwise it sets the count.
3. desired = ceil(ratio x pods counted), kept between the fewest and the most pods.
4. Scaling down follows the highest recommendation of the last 300 s; scaling up follows the latest.
5. Scaling up is limited to the larger of +4 pods and doubling per sync.

The four signals are the metric in step 1: busy slots over slots (`utilization`, what GPU utilization stands in for),
requests in the system (`concurrency`), requests waiting (`queue`) and requests arriving per second over the last
30 s (`rps`).

**Workload.** [burst](../workloads/burst.json) is 30 minutes of arrivals drawn as a non-homogeneous Poisson process
from a rate schedule, with log-normal prompt and output lengths: a baseline of 3 requests per second, a ramp to 20
that lasts 4 minutes, a 10-minute quiet spell, a spike to 40 for 20 seconds that arrives after the autoscaler has
relaxed, and a second ramp. Each run uses its own seed; every policy in a run replays the same trace.

**Metrics.** Goodput is the share of requests whose first token arrives within 2 s. A 10-second window is unhealthy
when the p95 of the requests that arrived in it misses that objective. Cost is replica-seconds. A flap is a
scale-up within 120 s of a scale-down.

## What was decided before the results, and what changed after

Chosen before any run was compared, and not tuned afterwards: the pod model above, the 2 s objective, the targets of
the four signals (utilization 0.6, concurrency 6, queue 1, requests per second 1.4), the 24-pod static pool (the peak of
40 requests per second at about 1.9 requests per second per pod, plus headroom), and the 2 to 32 bounds.

Changed after a first look: the workload was first 10 minutes long. A 10-minute trace cannot show scale-down against
a 300 s window, because the pods the burst created are still there when it ends, so every policy cost almost the same
as the static pool. It is 30 minutes now, with the spike placed after the autoscaler has relaxed. That is a change to
the workload, not to any policy, and the first trace's numbers are not reported.

The signals were each run at one pre-chosen target, so [the signals dataset](../results/signals/README.md) ranks
those four settings, not the four signals in general. [The targets dataset](../results/targets/README.md) shows how
far one signal moves when its target does.

## What it cannot tell you

- **Absolute numbers belong to the model.** A p95 of 47 s is what this pod model, this trace and this controller give;
  your pods, models and traffic will differ. The comparisons, and the way each one moves when a setting changes, are
  the result.
- **Slowdowns are measured at the start of a request.** A real batch changes as requests arrive and leave. The error
  is the same for every policy.
- **There is no router, prefix cache, network or metrics delay.** The autoscaler sees the exact state at each sync.
  A real metrics pipeline adds a scrape interval and usually more, which makes every policy here look better than it would be.
- **There is no KEDA, Knative or predictive scaling.** They are different controllers around the same signals. The
  HPA is modelled because it is what most clusters run.
- **One workload.** A different trace changes the numbers, and a gentler ramp changes the conclusions.

A cluster stage, with real pods and the Kubernetes controller, is the next step; until it exists nothing here is
measured on a cluster.
