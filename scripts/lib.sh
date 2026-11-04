# Sourced by every cluster script: the pinned versions, and a refusal to touch any cluster but the benchmark's.
# shellcheck shell=bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
# shellcheck source=../deploy/versions.env
. "$ROOT/deploy/versions.env"
set +a
NS=iab
MONITORING_NS=monitoring

require_context() {
  local current
  current="$(kubectl config current-context 2>/dev/null || true)"
  if [ "$current" != "$KIND_CONTEXT" ]; then
    echo "refusing to run: kubectl context is '$current', not '$KIND_CONTEXT' (scripts/cluster-up.sh creates it)" >&2
    exit 1
  fi
}
