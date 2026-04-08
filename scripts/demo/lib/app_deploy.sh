#!/usr/bin/env bash

set -euo pipefail

APP_DEPLOYMENTS=(backend frontend order-ingest notification-service asset-service)
APP_STATEFULSETS=(postgres)

app_create_namespace() {
  kubectl_cmd create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl_cmd apply -f - >/dev/null
  log "Namespace ${NAMESPACE} ready"
}

app_create_secrets() {
  log "Creating demo secrets"
  NAMESPACE="${NAMESPACE}" \
  DEMO_ADMIN_EMAIL="${DEMO_ADMIN_EMAIL:-admin@example.com}" \
  DEMO_ADMIN_PASSWORD="${DEMO_ADMIN_PASSWORD:-C1sco12345}" \
  SPLUNK_RUM_ACCESS_TOKEN="${SPLUNK_RUM_ACCESS_TOKEN:-}" \
    bash "${repo_root}/k8s/3dprint/create-demo-secret.sh" >/dev/null
}

app_create_configmaps() {
  local script
  for script in \
    "${repo_root}/k8s/3dprint/create-notification-service-configmap.sh" \
    "${repo_root}/k8s/3dprint/create-asset-service-configmap.sh" \
    "${repo_root}/k8s/3dprint/create-order-ingest-configmap.sh" \
    "${repo_root}/k8s/3dprint/create-loadgen-manifest-configmap.sh"
  do
    log "Running $(basename "${script}")"
    NAMESPACE="${NAMESPACE}" bash "${script}" >/dev/null
  done
}

app_apply_manifests() {
  log "Applying kustomize manifests"
  kubectl_cmd apply -k "${repo_root}/k8s/3dprint" >/dev/null
}

app_wait_ready() {
  local timeout="${APP_ROLLOUT_TIMEOUT:-5m}"
  local resource

  for resource in "${APP_STATEFULSETS[@]}"; do
    if kubectl_cmd -n "${NAMESPACE}" get statefulset "${resource}" >/dev/null 2>&1; then
      log "Waiting for statefulset/${resource}"
      kubectl_cmd -n "${NAMESPACE}" rollout status "statefulset/${resource}" --timeout="${timeout}" >/dev/null
    fi
  done

  for resource in "${APP_DEPLOYMENTS[@]}"; do
    if kubectl_cmd -n "${NAMESPACE}" get deploy "${resource}" >/dev/null 2>&1; then
      log "Waiting for deploy/${resource}"
      kubectl_cmd -n "${NAMESPACE}" rollout status "deploy/${resource}" --timeout="${timeout}" >/dev/null
    fi
  done

  log "All app workloads rolled out"
}

app_health_check() {
  local attempts=12
  local sleep_seconds=10
  local current_attempt=1
  local health_url
  local http_code

  health_url="$(safe_api_base_url)/health"
  log "Health-checking backend at ${health_url}"

  while (( current_attempt <= attempts )); do
    http_code="$(curl -sS -o /dev/null -w '%{http_code}' "${health_url}" 2>/dev/null || printf '000')"
    if [[ "${http_code}" == "200" ]]; then
      log "Backend health check passed"
      return 0
    fi
    log "  attempt ${current_attempt}/${attempts}: HTTP ${http_code}, retrying in ${sleep_seconds}s"
    sleep "${sleep_seconds}"
    current_attempt=$((current_attempt + 1))
  done

  warn "Backend health check did not return 200 after ${attempts} attempts; the app may still be starting"
}

app_deploy() {
  require_cmd kubectl
  app_create_namespace
  app_create_secrets
  app_create_configmaps
  app_apply_manifests
  app_wait_ready
  app_health_check
  log "App deployment complete"
}

app_teardown() {
  require_cmd kubectl
  log "Deleting app namespace ${NAMESPACE}"
  kubectl_cmd delete namespace "${NAMESPACE}" --ignore-not-found 2>/dev/null || true
  log "App namespace removed"
}
