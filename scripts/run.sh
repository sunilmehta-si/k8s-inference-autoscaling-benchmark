#!/usr/bin/env bash
# One policy and seed, start to finish, on the cluster scripts/cluster-up.sh made: servers, monitoring, the autoscaler,
# then the load client, with the cluster sampled throughout.
# Usage: scripts/run.sh POLICY SEED WORKLOAD_JSON OUT_JSON
#   POLICY is static-N or hpa-SIGNAL (concurrency, queue, utilization).
#   Environment: STARTUP_S (45), MIN_REPLICAS (2), MAX_REPLICAS (32), DOWN_WINDOW_S (300).
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

policy="${1:?usage: run.sh POLICY SEED WORKLOAD_JSON OUT_JSON}" seed="${2:?seed}" workload="${3:?workload}" out="${4:?out}"
case "$policy" in
  static-[0-9]*) replicas="${policy#static-}"; signal="" ;;
  hpa-*)         replicas="${MIN_REPLICAS:-2}"; signal="${policy#hpa-}" ;;
  *) echo "unknown policy '$policy': use static-N or hpa-SIGNAL" >&2; exit 1 ;;
esac
export STARTUP_S="${STARTUP_S:-45}"

scripts/deploy-servers.sh "$replicas"
scripts/deploy-monitoring.sh
if [ -n "$signal" ]; then
  scripts/apply-hpa.sh "$signal"
  # The autoscaler acts on nothing until it can read the signal: wait for that before the first request, so the
  # run measures the autoscaler and not how long the metrics path took to warm up.
  deadline=$((SECONDS + 420))
  until [ -n "$(kubectl -n "$NS" get hpa sim -o jsonpath='{.status.currentMetrics[0].pods.current.averageValue}' 2>/dev/null)" ]; do
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "the autoscaler never read the $signal metric:" >&2
      kubectl -n "$NS" describe hpa sim >&2 || true
      exit 1
    fi
    sleep 5
  done
  echo "the autoscaler reads the $signal metric"
fi
python3 -m inference_autoscaling_bench cluster-run --policy "$policy" --seed "$seed" --workload "$workload" --out "$out"
