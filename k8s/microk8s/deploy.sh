#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NAMESPACE="3dprint"
TAG="local"

# ── Helpers ──────────────────────────────────────────────────────────

info()  { printf '\033[1;34m==> %s\033[0m\n' "$*"; }
ok()    { printf '\033[1;32m    ✓ %s\033[0m\n' "$*"; }
warn()  { printf '\033[1;33m    ⚠ %s\033[0m\n' "$*"; }
fail()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

mk() { microk8s kubectl "$@"; }

require_microk8s() {
  command -v microk8s >/dev/null 2>&1 || fail "microk8s not found. Install it first: https://microk8s.io/docs/getting-started"
  microk8s status --wait-ready >/dev/null 2>&1 || fail "microk8s is not running. Start it with: microk8s start"
  ok "microk8s is running"
}

enable_addon() {
  local addon="$1"
  info "Ensuring addon enabled: ${addon}"
  microk8s enable "$addon"
  ok "addon ${addon} ready"
}

# ── Image Build + Import ─────────────────────────────────────────────

build_images() {
  info "Building Docker images"

  local images=(
    "filaops-backend:${REPO_ROOT}/backend"
    "filaops-frontend:${REPO_ROOT}/frontend"
    "filaops-asset-service:${REPO_ROOT}/asset-service"
    "filaops-order-ingest:${REPO_ROOT}/order-ingest"
    "filaops-notification-service:${REPO_ROOT}/notification-service"
    "filaops-pricing-service:${REPO_ROOT}/pricing-service"
  )

  for entry in "${images[@]}"; do
    local name="${entry%%:*}"
    local context="${entry#*:}"
    local full_tag="${name}:${TAG}"

    info "Building ${full_tag} from ${context}"
    if [[ "${name}" == "filaops-frontend" ]]; then
      docker build -t "${full_tag}" --build-arg "VITE_API_URL=" "${context}"
    else
      docker build -t "${full_tag}" "${context}"
    fi
    ok "${full_tag}"
  done
}

import_images() {
  info "Importing images into MicroK8s"

  local names=(
    filaops-backend
    filaops-frontend
    filaops-asset-service
    filaops-order-ingest
    filaops-notification-service
    filaops-pricing-service
  )

  for name in "${names[@]}"; do
    local full_tag="${name}:${TAG}"
    info "Importing ${full_tag}"
    docker save "${full_tag}" | microk8s ctr image import -
    ok "${full_tag}"
  done
}

# ── Secrets ──────────────────────────────────────────────────────────

ensure_kubectl_shim() {
  if command -v kubectl >/dev/null 2>&1; then
    return
  fi
  KUBECTL_SHIM_DIR="$(mktemp -d)"
  cat > "${KUBECTL_SHIM_DIR}/kubectl" <<'SHIM'
#!/bin/sh
exec microk8s kubectl "$@"
SHIM
  chmod +x "${KUBECTL_SHIM_DIR}/kubectl"
  export PATH="${KUBECTL_SHIM_DIR}:${PATH}"
}

create_secrets() {
  info "Creating namespace and secrets"

  ensure_kubectl_shim

  local secret_script="${REPO_ROOT}/k8s/3dprint/create-demo-secret.sh"
  if [[ -f "${secret_script}" ]]; then
    NAMESPACE="${NAMESPACE}" bash "${secret_script}"
    ok "Secrets created via create-demo-secret.sh"
  else
    warn "create-demo-secret.sh not found, creating minimal secret"
    mk create namespace "${NAMESPACE}" --dry-run=client -o yaml | mk apply -f -

    mk -n "${NAMESPACE}" create secret generic filaops-secrets \
      --from-literal=DB_NAME=filaops \
      --from-literal=DB_USER=postgres \
      --from-literal=DB_PASSWORD="$(openssl rand -hex 16)" \
      --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
      --from-literal=DEMO_ADMIN_ENABLED=true \
      --from-literal=DEMO_ADMIN_EMAIL=admin@example.com \
      --from-literal=DEMO_ADMIN_PASSWORD="$(openssl rand -hex 12)" \
      --from-literal=DEMO_ADMIN_FULL_NAME="Local Admin" \
      --from-literal=DEMO_ADMIN_COMPANY_NAME="MicroK8s Dev" \
      --from-literal=NOTIFICATION_SERVICE_TOKEN="$(openssl rand -hex 24)" \
      --from-literal=ASSET_SERVICE_TOKEN="$(openssl rand -hex 24)" \
      --from-literal=ORDER_INGEST_SERVICE_TOKEN="$(openssl rand -hex 24)" \
      --from-literal=PRICING_SERVICE_TOKEN="$(openssl rand -hex 24)" \
      --from-literal=SPLUNK_RUM_ACCESS_TOKEN="" \
      --dry-run=client -o yaml | mk apply -f -
    ok "Minimal secrets created"
  fi
}

# ── Deploy ───────────────────────────────────────────────────────────

do_deploy() {
  info "FilaOps MicroK8s Deploy"
  echo ""

  require_microk8s

  info "Checking required addons"
  enable_addon dns
  enable_addon hostpath-storage

  build_images
  import_images
  create_secrets

  info "Applying Kustomize manifests"
  mk apply -k "${SCRIPT_DIR}"
  ok "Manifests applied"

  info "Waiting for rollouts"
  mk -n "${NAMESPACE}" rollout status statefulset/db --timeout=120s || warn "db not ready yet"
  mk -n "${NAMESPACE}" rollout status deployment/backend --timeout=180s || warn "backend not ready yet"
  mk -n "${NAMESPACE}" rollout status deployment/frontend --timeout=120s || warn "frontend not ready yet"
  for svc in asset-service notification-service order-ingest pricing-service; do
    mk -n "${NAMESPACE}" rollout status "deployment/${svc}" --timeout=120s || warn "${svc} not ready yet"
  done

  echo ""
  ok "FilaOps is deployed on MicroK8s"
  echo ""
  echo "  Frontend:  http://localhost:30080"
  echo "  API:       http://localhost:30080/api/v1"
  echo ""
  echo "  Status:    $0 status"
  echo "  Teardown:  $0 teardown"
  echo ""
}

# ── Teardown ─────────────────────────────────────────────────────────

do_teardown() {
  info "Tearing down FilaOps from MicroK8s"
  require_microk8s

  if mk get namespace "${NAMESPACE}" >/dev/null 2>&1; then
    mk delete namespace "${NAMESPACE}" --timeout=120s
    ok "Namespace ${NAMESPACE} deleted"
  else
    warn "Namespace ${NAMESPACE} does not exist"
  fi

  echo ""
  ok "Teardown complete"
  echo ""
}

# ── Status ───────────────────────────────────────────────────────────

do_status() {
  require_microk8s

  echo ""
  info "Pods"
  mk -n "${NAMESPACE}" get pods -o wide 2>/dev/null || warn "No pods found"
  echo ""
  info "Services"
  mk -n "${NAMESPACE}" get svc 2>/dev/null || warn "No services found"
  echo ""
  info "PersistentVolumeClaims"
  mk -n "${NAMESPACE}" get pvc 2>/dev/null || warn "No PVCs found"
  echo ""
}

# ── Rebuild (images only, then restart) ──────────────────────────────

do_rebuild() {
  info "Rebuilding images and restarting deployments"
  require_microk8s

  build_images
  import_images

  info "Restarting deployments"
  for dep in backend frontend asset-service notification-service order-ingest pricing-service; do
    mk -n "${NAMESPACE}" rollout restart "deployment/${dep}" 2>/dev/null || true
  done
  mk -n "${NAMESPACE}" rollout restart "statefulset/db" 2>/dev/null || true

  ok "Restart triggered — watch with: $0 status"
  echo ""
}

# ── Main ─────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  deploy    Build images, create secrets, and apply manifests
  teardown  Delete the ${NAMESPACE} namespace and all resources
  status    Show pod, service, and PVC status
  rebuild   Rebuild images and restart deployments (no manifest changes)
  help      Show this message

Prerequisites:
  - MicroK8s installed and running
  - Docker installed (for building images)

EOF
}

case "${1:-help}" in
  deploy)   do_deploy   ;;
  teardown) do_teardown ;;
  status)   do_status   ;;
  rebuild)  do_rebuild  ;;
  help|-h)  usage       ;;
  *)        fail "Unknown command: $1. Run '$0 help' for usage." ;;
esac
