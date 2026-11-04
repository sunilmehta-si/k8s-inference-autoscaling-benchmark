#!/usr/bin/env bash
# Check the whole metrics path end to end with no load: the pods' metrics reach Prometheus, the recording rules produce
# one series per signal, the custom metrics API serves them, and the Horizontal Pod Autoscaler reads one.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

query() {  # a Prometheus instant query through the API server's service proxy: no port-forward, no extra pod
  kubectl get --raw "/api/v1/namespaces/$MONITORING_NS/services/prometheus:9090/proxy/api/v1/query?query=$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1")"
}
value() {
  query "$1" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else "")'
}
wait_for() {  # wait_for DESCRIPTION SECONDS COMMAND...
  local what="$1" limit="$2"; shift 2
  local deadline=$((SECONDS + limit))
  until "$@"; do
    if [ "$SECONDS" -ge "$deadline" ]; then echo "timed out waiting for $what" >&2; return 1; fi
    sleep 5
  done
  echo "ok: $what"
}

pods="$(kubectl -n "$NS" get pods -l app=sim --no-headers | wc -l | tr -d ' ')"
targets_up() { [ "$(value 'count(up{job="sim"} == 1)')" = "$pods" ]; }
has_series() { [ -n "$(value "$1")" ]; }
api_serves() { kubectl get --raw /apis/custom.metrics.k8s.io/v1beta2 | grep -q 'pods/concurrency'; }
metric_value() { kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta2/namespaces/$NS/pods/*/concurrency" | python3 -c 'import sys,json; items=json.load(sys.stdin)["items"]; assert items, "no items"; print(len(items))' >/dev/null 2>&1; }
hpa_reads() { [ -n "$(kubectl -n "$NS" get hpa sim -o jsonpath='{.status.currentMetrics[0].pods.current.averageValue}' 2>/dev/null)" ]; }

fail() {
  echo "--- diagnostics" >&2
  query 'up{job="sim"}' >&2 || true
  kubectl -n "$MONITORING_NS" logs deployment/prometheus-adapter --tail=40 >&2 || true
  kubectl -n "$MONITORING_NS" logs deployment/prometheus --tail=20 >&2 || true
  kubectl get apiservice v1beta2.custom.metrics.k8s.io -o yaml >&2 || true
  kubectl -n "$NS" describe hpa sim >&2 || true
  first="$(kubectl -n "$NS" get pods -l app=sim -o name | head -1)"
  kubectl get --raw "/api/v1/namespaces/$NS/pods/${first#pod/}:8000/proxy/metrics" 2>&1 | grep -E '^(vllm:num_requests|# HELP vllm:num_requests)' >&2 || true
  exit 1
}
trap fail ERR

wait_for "Prometheus scrapes all $pods model servers" 120 targets_up
wait_for "the pods publish vllm:num_requests_running" 60 has_series 'count(vllm:num_requests_running)'
wait_for "the recording rule iab_concurrency has a series per pod" 90 has_series 'count(iab_concurrency)'
wait_for "the custom metrics API lists the concurrency metric" 180 api_serves
wait_for "the custom metrics API returns it for the pods" 60 metric_value
scripts/apply-hpa.sh concurrency
wait_for "the Horizontal Pod Autoscaler reads the metric" 120 hpa_reads
kubectl -n "$NS" get hpa sim
echo "metrics path OK: pods -> Prometheus -> recording rule -> adapter -> custom metrics API -> autoscaler"
