#!/usr/bin/env bash
# Build the load client's image and load it into the kind cluster.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

name="${KIND_CONTEXT#kind-}"
docker build -q --build-arg "PYTHON_IMAGE=${PYTHON_IMAGE}" -t iab-client:dev . >/dev/null
kind load docker-image iab-client:dev --name "$name" >/dev/null
echo "load client image loaded: iab-client:dev"
