#!/usr/bin/env bash
# (Re)create the simulated model servers: REPLICAS pods, each not ready until STARTUP_S seconds after it starts, which
# stands in for scheduling, pulling the image and loading the model.
# Usage: scripts/deploy-servers.sh [REPLICAS]   (default 2; STARTUP_S default 45)
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

export REPLICAS="${1:-2}"
export STARTUP_S="${STARTUP_S:-45}"
kubectl -n "$NS" delete hpa sim --ignore-not-found >/dev/null 2>&1 || true
kubectl -n "$NS" delete deployment sim --ignore-not-found --wait=true >/dev/null 2>&1 || true
envsubst '${SIM_IMAGE} ${REPLICAS} ${STARTUP_S}' < deploy/servers.yaml | kubectl apply -f - >/dev/null
if ! kubectl -n "$NS" rollout status deployment/sim --timeout=300s >/dev/null; then
  echo "the model servers did not become ready:" >&2
  kubectl -n "$NS" get pods -o wide >&2 || true
  kubectl -n "$NS" logs deployment/sim --tail=40 >&2 || true
  exit 1
fi
echo "model servers ready: $REPLICAS simulated vLLM pods (${SIM_IMAGE%@*}), ${STARTUP_S}s to become ready"
