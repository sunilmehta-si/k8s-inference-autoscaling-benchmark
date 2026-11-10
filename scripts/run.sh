#!/usr/bin/env bash
# One policy and seed, start to finish, on the cluster scripts/cluster-up.sh made: servers, monitoring, the autoscaler,
# then the load client, with the cluster sampled throughout.
# Usage: scripts/run.sh POLICY SEED WORKLOAD_JSON OUT_JSON
#   POLICY is static-N, hpa-SIGNAL or keda-SIGNAL (concurrency, queue, utilization).
#   Environment: STARTUP_S (45), MIN_REPLICAS (2), MAX_REPLICAS (32), DOWN_WINDOW_S (300).
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

policy="${1:?usage: run.sh POLICY SEED WORKLOAD_JSON OUT_JSON}" seed="${2:?seed}" workload="${3:?workload}" out="${4:?out}"
case "$policy" in
  static-[0-9]*) replicas="${policy#static-}"; signal="" ;;
  hpa-*)         replicas="${MIN_REPLICAS:-2}"; signal="${policy#hpa-}"; scaler=hpa ;;
  keda-*)        replicas="${MIN_REPLICAS:-2}"; signal="${policy#keda-}"; scaler=keda ;;
  *) echo "unknown policy '$policy': use static-N, hpa-SIGNAL or keda-SIGNAL" >&2; exit 1 ;;
esac
export STARTUP_S="${STARTUP_S:-45}"

scripts/deploy-servers.sh "$replicas"
scripts/deploy-monitoring.sh
if [ -n "$signal" ]; then
  # Both autoscalers are a Horizontal Pod Autoscaler: the HPA reads a pods metric named for the signal from the
  # adapter, the one KEDA creates reads an external metric from KEDA.
  if [ "$scaler" = keda ]; then
    scripts/deploy-keda.sh
    scripts/apply-keda.sh "$signal"
    hpa=keda-hpa-sim value='{.status.currentMetrics[0].external.current.averageValue}'
  else
    scripts/apply-hpa.sh "$signal"
    hpa=sim value='{.status.currentMetrics[0].pods.current.averageValue}'
  fi
  # The autoscaler acts on nothing until it can read the signal: wait for that before the first request, so the
  # run measures the autoscaler and not how long the metrics path took to warm up.
  deadline=$((SECONDS + 420))
  until [ -n "$(kubectl -n "$NS" get hpa "$hpa" -o jsonpath="$value" 2>/dev/null)" ]; do
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "the autoscaler never read the $signal metric:" >&2
      kubectl -n "$NS" describe hpa "$hpa" >&2 || true
      exit 1
    fi
    sleep 5
  done
  echo "the autoscaler ($scaler) reads the $signal metric"
fi
python3 -m inference_autoscaling_bench cluster-run --policy "$policy" --seed "$seed" --workload "$workload" --out "$out"
