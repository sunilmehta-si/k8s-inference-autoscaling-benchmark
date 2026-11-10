#!/usr/bin/env bash
# Check the adapter's external path end to end with no load: the adapter serves concurrency_sum through the external
# metrics API, and the HPA reading it as an external metric gets a value. Run after scripts/smoke.sh, on a cluster
# without KEDA; it replaces the smoke test's HPA with the external one.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

wait_for() {  # wait_for DESCRIPTION SECONDS COMMAND...
  local what="$1" limit="$2"; shift 2
  local deadline=$((SECONDS + limit))
  until "$@"; do
    if [ "$SECONDS" -ge "$deadline" ]; then echo "timed out waiting for $what" >&2; return 1; fi
    sleep 5
  done
  echo "ok: $what"
}
api_serves_the_sum() {
  kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/$NS/concurrency_sum" 2>/dev/null \
    | python3 -c 'import sys,json; assert json.load(sys.stdin)["items"]' 2>/dev/null
}
hpa_reads() {
  [ -n "$(kubectl -n "$NS" get hpa sim -o jsonpath='{.status.currentMetrics[0].external.current.averageValue}' 2>/dev/null)" ]
}

fail() {
  echo "--- diagnostics" >&2
  kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml >&2 || true
  kubectl -n "$MONITORING_NS" logs deployment/prometheus-adapter --tail=40 >&2 || true
  kubectl -n "$NS" describe hpa sim >&2 || true
  exit 1
}
trap fail ERR

scripts/apply-external.sh concurrency
wait_for "the external metrics API serves concurrency_sum" 180 api_serves_the_sum
wait_for "the HPA reads the sum as an external metric" 120 hpa_reads
kubectl -n "$NS" get hpa sim
echo "adapter external path OK: pods -> Prometheus -> recording rule -> adapter (sum) -> external metrics API -> autoscaler"
