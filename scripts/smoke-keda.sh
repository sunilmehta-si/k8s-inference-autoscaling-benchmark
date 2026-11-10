#!/usr/bin/env bash
# Check KEDA's path end to end with no load: KEDA installs and serves the external metrics API, a ScaledObject on the
# concurrency signal gets its autoscaler, and that autoscaler reads the sum Prometheus records, as an average per pod.
# Run after scripts/deploy-servers.sh and scripts/deploy-monitoring.sh, on a cluster with no other autoscaler.
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
external_metrics() { kubectl get --raw /apis/external.metrics.k8s.io/v1beta1 >/dev/null 2>&1; }
hpa_reads() {
  [ -n "$(kubectl -n "$NS" get hpa keda-hpa-sim -o jsonpath='{.status.currentMetrics[0].external.current.averageValue}' 2>/dev/null)" ]
}
scaled_object_ready() {
  [ "$(kubectl -n "$NS" get scaledobject sim -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)" = True ]
}

fail() {
  echo "--- diagnostics" >&2
  kubectl -n "$NS" describe scaledobject sim >&2 || true
  kubectl -n "$NS" describe hpa keda-hpa-sim >&2 || true
  kubectl -n keda logs deployment/keda-operator --tail=60 >&2 || true
  kubectl -n keda logs deployment/keda-metrics-apiserver --tail=30 >&2 || true
  kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml >&2 || true
  exit 1
}
trap fail ERR

kubectl -n "$NS" delete hpa sim --ignore-not-found >/dev/null   # one autoscaler per Deployment
scripts/deploy-keda.sh
wait_for "the external metrics API answers" 60 external_metrics
scripts/apply-keda.sh concurrency
wait_for "the ScaledObject is ready" 120 scaled_object_ready
wait_for "KEDA's autoscaler reads the external metric" 180 hpa_reads
kubectl -n "$NS" get scaledobject,hpa
echo "KEDA path OK: pods -> Prometheus -> recording rule -> KEDA -> external metrics API -> autoscaler"
