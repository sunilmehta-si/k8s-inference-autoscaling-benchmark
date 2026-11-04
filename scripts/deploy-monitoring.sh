#!/usr/bin/env bash
# Prometheus, the recording rules and prometheus-adapter, and wait until the custom metrics API is serving.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

envsubst '${PROMETHEUS_IMAGE} ${PROMETHEUS_ADAPTER_IMAGE}' < deploy/monitoring.yaml | kubectl apply -f - >/dev/null
for deploy in prometheus prometheus-adapter; do
  if ! kubectl -n "$MONITORING_NS" rollout status "deployment/$deploy" --timeout=300s >/dev/null; then
    echo "$deploy did not become ready:" >&2
    kubectl -n "$MONITORING_NS" describe "deployment/$deploy" | tail -20 >&2 || true
    kubectl -n "$MONITORING_NS" logs "deployment/$deploy" --tail=60 >&2 || true
    exit 1
  fi
done
echo "monitoring ready: Prometheus ${PROMETHEUS_VERSION}, prometheus-adapter ${PROMETHEUS_ADAPTER_VERSION}"
