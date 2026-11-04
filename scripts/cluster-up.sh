#!/usr/bin/env bash
# Create the kind cluster (unless it exists) and switch to it. Run it in CI: on a machine whose kubectl points at a real
# cluster it still only ever creates and uses the kind-iab context, and every other script refuses any other.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
cd "$ROOT"

name="${KIND_CONTEXT#kind-}"
if ! kind get clusters 2>/dev/null | grep -qx "$name"; then
  kind create cluster --name "$name" --image "$KIND_NODE_IMAGE" --wait 120s
fi
kubectl config use-context "$KIND_CONTEXT" >/dev/null
require_context
echo "cluster ready: ${KIND_CONTEXT}, $(kubectl version -o json | python3 -c 'import sys,json; print(json.load(sys.stdin)["serverVersion"]["gitVersion"])')"
