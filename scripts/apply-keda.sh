#!/usr/bin/env bash
# Put KEDA, scaling on one signal, in front of the model servers. KEDA creates the Horizontal Pod Autoscaler itself
# (keda-hpa-sim); this waits until it exists.
# Usage: scripts/apply-keda.sh SIGNAL   (concurrency; MIN_REPLICAS 2, MAX_REPLICAS 32, DOWN_WINDOW_S 300 by default)
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

signal="${1:?usage: apply-keda.sh SIGNAL}"
[ -f "deploy/keda/$signal.yaml" ] || { echo "no deploy/keda/$signal.yaml" >&2; exit 1; }
export MIN_REPLICAS="${MIN_REPLICAS:-2}" MAX_REPLICAS="${MAX_REPLICAS:-32}" DOWN_WINDOW_S="${DOWN_WINDOW_S:-300}"
envsubst '${MIN_REPLICAS} ${MAX_REPLICAS} ${DOWN_WINDOW_S}' < "deploy/keda/$signal.yaml" | kubectl apply -f - >/dev/null
deadline=$((SECONDS + 120))
until kubectl -n "$NS" get hpa keda-hpa-sim >/dev/null 2>&1; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "KEDA did not create its autoscaler:" >&2
    kubectl -n "$NS" describe scaledobject sim >&2 || true
    kubectl -n keda logs deployment/keda-operator --tail=40 >&2 || true
    exit 1
  fi
  sleep 3
done
echo "KEDA applied: $signal, ${MIN_REPLICAS} to ${MAX_REPLICAS} pods, scale-down window ${DOWN_WINDOW_S}s"
