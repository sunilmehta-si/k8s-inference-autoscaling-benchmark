#!/usr/bin/env bash
# Put the Horizontal Pod Autoscaler in front of the model servers reading one signal's sum over the pods as an external
# metric from prometheus-adapter: KEDA's arithmetic on the adapter's path. Never on a cluster with KEDA, which serves the
# same API.
# Usage: scripts/apply-external.sh SIGNAL   (concurrency; MIN_REPLICAS 2, MAX_REPLICAS 32, DOWN_WINDOW_S 300 by default)
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

signal="${1:?usage: apply-external.sh SIGNAL}"
[ -f "deploy/hpa-external/$signal.yaml" ] || { echo "no deploy/hpa-external/$signal.yaml" >&2; exit 1; }
if kubectl get namespace keda >/dev/null 2>&1; then
  echo "KEDA is installed and serves the external metrics API; run an external- policy on a cluster without it" >&2
  exit 1
fi
kubectl apply -f deploy/adapter-external.yaml >/dev/null
if ! kubectl wait apiservice/v1beta1.external.metrics.k8s.io --for=condition=Available --timeout=180s >/dev/null; then
  echo "the adapter's external metrics API is not available:" >&2
  kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml >&2 || true
  exit 1
fi
export MIN_REPLICAS="${MIN_REPLICAS:-2}" MAX_REPLICAS="${MAX_REPLICAS:-32}" DOWN_WINDOW_S="${DOWN_WINDOW_S:-300}"
envsubst '${MIN_REPLICAS} ${MAX_REPLICAS} ${DOWN_WINDOW_S}' < "deploy/hpa-external/$signal.yaml" | kubectl apply -f - >/dev/null
echo "autoscaler applied: ${signal}_sum as an external metric from the adapter, ${MIN_REPLICAS} to ${MAX_REPLICAS} pods, scale-down window ${DOWN_WINDOW_S}s"
