#!/usr/bin/env bash
# KEDA from its release manifest: downloaded, checked against the pinned checksum, its three images swapped for the
# pinned digests, applied, and waited for until the external metrics API is serving.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
require_context
cd "$ROOT"

tag="${KEDA_VERSION#v}"
manifest="$(mktemp)"
trap 'rm -f "$manifest"' EXIT
curl -sSfL -o "$manifest" "https://github.com/kedacore/keda/releases/download/${KEDA_VERSION}/keda-${tag}.yaml"
echo "${KEDA_MANIFEST_SHA256}  $manifest" | sha256sum -c - >/dev/null
for pair in "keda:${KEDA_IMAGE}" "keda-metrics-apiserver:${KEDA_METRICS_APISERVER_IMAGE}" \
            "keda-admission-webhooks:${KEDA_ADMISSION_WEBHOOKS_IMAGE}"; do
  name="${pair%%:*}" pinned="${pair#*:}"
  [ "$(grep -c "image: ghcr.io/kedacore/${name}:${tag}$" "$manifest")" = 1 ] \
    || { echo "the KEDA manifest does not name ghcr.io/kedacore/${name}:${tag} exactly once" >&2; exit 1; }
  sed -i "s|image: ghcr.io/kedacore/${name}:${tag}$|image: ${pinned}|" "$manifest"
done
# The CRDs are too large for the annotation a client-side apply keeps, so KEDA's own instructions apply it server-side.
kubectl apply --server-side -f "$manifest" >/dev/null
# KEDA's containers meet the restricted standard, so its namespace enforces it like the benchmark's own.
kubectl label namespace keda pod-security.kubernetes.io/enforce=restricted --overwrite >/dev/null
for deploy in keda-operator keda-metrics-apiserver keda-admission; do
  if ! kubectl -n keda rollout status "deployment/$deploy" --timeout=300s >/dev/null; then
    echo "$deploy did not become ready:" >&2
    kubectl -n keda describe "deployment/$deploy" | tail -20 >&2 || true
    kubectl -n keda logs "deployment/$deploy" --tail=60 >&2 || true
    exit 1
  fi
done
if ! kubectl wait apiservice/v1beta1.external.metrics.k8s.io --for=condition=Available --timeout=180s >/dev/null; then
  echo "the external metrics API is not available:" >&2
  kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml >&2 || true
  exit 1
fi
echo "KEDA ready: ${KEDA_VERSION}, external metrics API available"
