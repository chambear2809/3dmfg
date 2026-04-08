#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

NAMESPACE="${NAMESPACE:-3dprint}"
CONFIGMAP_NAME="${CONFIGMAP_NAME:-asset-service-bundle}"
SERVICE_ROOT="${SERVICE_ROOT:-${repo_root}/asset-service}"

required_files=(
  "${SERVICE_ROOT}/requirements.txt"
  "${SERVICE_ROOT}/app/__init__.py"
  "${SERVICE_ROOT}/app/auth.py"
  "${SERVICE_ROOT}/app/config.py"
  "${SERVICE_ROOT}/app/main.py"
  "${SERVICE_ROOT}/app/models.py"
  "${SERVICE_ROOT}/app/storage.py"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "${file}" ]]; then
    echo "Required file not found: ${file}" >&2
    exit 1
  fi
done

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create configmap "${CONFIGMAP_NAME}" \
  --from-file=requirements.txt="${SERVICE_ROOT}/requirements.txt" \
  --from-file=app_init_py="${SERVICE_ROOT}/app/__init__.py" \
  --from-file=app_auth_py="${SERVICE_ROOT}/app/auth.py" \
  --from-file=app_config_py="${SERVICE_ROOT}/app/config.py" \
  --from-file=app_main_py="${SERVICE_ROOT}/app/main.py" \
  --from-file=app_models_py="${SERVICE_ROOT}/app/models.py" \
  --from-file=app_storage_py="${SERVICE_ROOT}/app/storage.py" \
  --dry-run=client -o yaml | kubectl apply -f -

cat <<EOF
Created/updated configmap ${CONFIGMAP_NAME} in namespace ${NAMESPACE}
requirements.txt <= ${SERVICE_ROOT}/requirements.txt
app/__init__.py <= ${SERVICE_ROOT}/app/__init__.py
app/auth.py <= ${SERVICE_ROOT}/app/auth.py
app/config.py <= ${SERVICE_ROOT}/app/config.py
app/main.py <= ${SERVICE_ROOT}/app/main.py
app/models.py <= ${SERVICE_ROOT}/app/models.py
app/storage.py <= ${SERVICE_ROOT}/app/storage.py
EOF
