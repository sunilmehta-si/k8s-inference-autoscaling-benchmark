#!/usr/bin/env bash
# Put the Horizontal Pod Autoscaler for one signal in front of the model servers.
# Usage: scripts/apply-hpa.sh SIGNAL   (concurrency; MIN_REPLICAS 2, MAX_REPLICAS 32, DOWN_WINDOW_S 300 by default)
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

signal="${1:?usage: apply-hpa.sh SIGNAL}"
[ -f "deploy/hpa/$signal.yaml" ] || { echo "no deploy/hpa/$signal.yaml" >&2; exit 1; }
export MIN_REPLICAS="${MIN_REPLICAS:-2}" MAX_REPLICAS="${MAX_REPLICAS:-32}" DOWN_WINDOW_S="${DOWN_WINDOW_S:-300}"
envsubst '${MIN_REPLICAS} ${MAX_REPLICAS} ${DOWN_WINDOW_S}' < "deploy/hpa/$signal.yaml" | kubectl apply -f - >/dev/null
echo "autoscaler applied: $signal, ${MIN_REPLICAS} to ${MAX_REPLICAS} pods, scale-down window ${DOWN_WINDOW_S}s"
