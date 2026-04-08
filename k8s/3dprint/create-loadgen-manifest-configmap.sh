#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

NAMESPACE="${NAMESPACE:-3dprint}"
CONFIGMAP_NAME="${CONFIGMAP_NAME:-loadgen-manifest}"
MANIFEST_PATH="${MANIFEST_PATH:-${repo_root}/scripts/loadgen/manifest.3dprint.json}"

if [[ ! -f "${MANIFEST_PATH}" ]]; then
  echo "Manifest not found at ${MANIFEST_PATH}" >&2
  exit 1
fi

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create configmap "${CONFIGMAP_NAME}" \
  --from-file=manifest.json="${MANIFEST_PATH}" \
  --dry-run=client -o yaml | kubectl apply -f -

cat <<EOF
Created/updated configmap ${CONFIGMAP_NAME} in namespace ${NAMESPACE}
manifest.json <= ${MANIFEST_PATH}
EOF
