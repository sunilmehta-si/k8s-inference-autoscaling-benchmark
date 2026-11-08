# The cluster stage

The simulation compares autoscaling settings on a model. The cluster stage runs the same policies, on the same seeded
traces, on a real Kubernetes control plane, so the model can be checked against something that is not the model.

## What runs

```
trace (seed) ──> load client (Job, in the cluster) ──> Service `sim` ──> simulated vLLM pods (Deployment `sim`)
                                                                              │ /metrics
                                  Horizontal Pod Autoscaler <── custom metrics API <── prometheus-adapter <── Prometheus
                                          │ sets replicas                                                  (recording rules)
                                          └──────────────────────────────────────────────> Deployment `sim`
```

**Real:** the API server, the Horizontal Pod Autoscaler controller and its algorithm, kube-proxy balancing connections,
Prometheus scraping every 15 s and evaluating its rules every 15 s, and prometheus-adapter serving the signals through the
custom metrics API. This is the metrics path a production cluster builds, with every hop's delay.

**Simulated:** the model servers. They are the [llm-d inference simulator](https://github.com/llm-d/llm-d-inference-sim)
configured to the simulation's shape (8 requests at once, 4,000 prompt tokens a second, 20 ms a token, slower as a pod
fills) and publishing vLLM's own metrics. A pod is not ready until `STARTUP_S` seconds after it starts, which stands in
for scheduling, pulling an image and loading a model.

Everything is pinned in [`deploy/versions.env`](../deploy/versions.env): images by digest, kind by checksum.

## What differs from the simulation

These are the differences a cluster run can show, and why a comparison is worth making:

- **Queues.** The simulation has one queue and a perfect router. On the cluster each pod queues its own requests and
  kube-proxy spreads connections without looking at load, so one pod can be idle while another has a queue.
- **Metrics delay.** The simulation's autoscaler sees the exact state at each sync unless a spec sets `lag`. On the
  cluster the signal is a scrape, a rule evaluation and a query behind the truth, and then the controller's own sync
  period. `iab compare` runs a third model with `lag=30`, the scrape interval plus the rule interval, and a fourth with
  `scrape=15`, in which each pod is scraped at its own offset, a rule evaluated at its own offset sums the latest
  samples, and the autoscaler reads the latest evaluation. `iab recompare DIR --workload W` runs the models again for a
  committed comparison after the model changes, without the cluster's raw runs.
- **One load factor.** The simulator slows every request by one factor as a pod fills, set to 1.55 at a full pod. The
  simulation slows prefill and decode separately, by about 1.44 and 1.53 at a full pod (0.5 and 0.6 times the share of
  the other slots that are busy).
- **Token counts.** The simulator's chat template adds a few tokens to each prompt, which the client records.
- **Pod removal.** The simulation drains a removed pod with nothing dropped; on the cluster a terminating pod is whatever
  the simulator does on `SIGTERM`, and any request it fails is counted as a miss.

## Running it

A run needs a kind cluster, so it runs in CI and only there: the scripts act only on the `kind-iab` context and refuse
any other, and a test holds that guard against a real cluster's context.

```bash
gh workflow run cluster-run.yml -f workload=burst -f 'policies=["hpa-concurrency","hpa-queue","static-24"]' -f 'seeds=[1,2,3]'
```

Each policy and seed gets its own cluster, so none inherits another's state, and uploads one JSON file as an artifact.
`scripts/run.sh POLICY SEED WORKLOAD OUT` is the whole run: servers, monitoring, the autoscaler, then the load client. For
an autoscaler it waits until the autoscaler can read the signal before the first request, so a run measures the
autoscaler and not how long the metrics path took to warm up.

A pull request that touches the runner replays the one-minute `smoke` workload through one policy, so the runner is
proven by the change that could break it.

## What a run records

- `summary`: the same metrics as a simulated run (goodput, time to first token percentiles, replica-seconds, unhealthy
  seconds, scaling events, flaps), computed by the same function, so the two are directly comparable. A request that got
  no answer counts as a miss and stays in the totals.
- `config`: the startup time, bounds and scale-down window the run was given, which `iab compare` gives the simulation too.
- `client`: requests sent and answered, how late the client sent the latest requests, and the prompt and output tokens
  requested against the tokens the server counted.
- `timeline`, `events`, `sampling`: the pods that existed, were ready, were starting, and the running and waiting requests,
  sampled every 5 s, and every change in the autoscaler's replica count.

`iab compare DIR --workload workloads/burst.json --out results/cluster` runs the simulation for each cluster run's policy,
seed and settings and writes the two side by side: median and range per metric, the difference, and a run-by-run table.

The ramps run the same way with `-f workload=ramp-30`, `ramp-120`, `ramp-300` or `ramp-600` and
`-f 'policies=["static-24","hpa-concurrency","hpa-utilization"]'`, and compare into `results/cluster-ramps/ramp-R` with the
matching workload file.

## Not reproducible to the digit

A simulation run is the same on every machine. A cluster run is not: a shared CI machine has its own timing. That is why
each policy runs on several seeds and the comparison shows ranges, and why a difference is claimed only when it holds in
every run.
