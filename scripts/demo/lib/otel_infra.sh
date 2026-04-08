#!/usr/bin/env bash

set -euo pipefail

CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.17.1}"
OTEL_OPERATOR_VERSION="${OTEL_OPERATOR_VERSION:-0.75.0}"
SPLUNK_OTEL_CHART_VERSION="${SPLUNK_OTEL_CHART_VERSION:-0.113.0}"

OTEL_COLLECTOR_NAMESPACE="${OTEL_COLLECTOR_NAMESPACE:-otel-splunk}"
OTEL_OPERATOR_NAMESPACE="${OTEL_OPERATOR_NAMESPACE:-opentelemetry-operator-system}"

otel_ensure_helm_repos() {
  helm repo add jetstack https://charts.jetstack.io --force-update 2>/dev/null || true
  helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts --force-update 2>/dev/null || true
  helm repo add splunk-otel-collector-chart https://signalfx.github.io/splunk-otel-collector-chart --force-update 2>/dev/null || true
  helm repo update >/dev/null 2>&1
}

otel_install_cert_manager() {
  if kubectl_cmd get crd certificates.cert-manager.io >/dev/null 2>&1; then
    log "cert-manager CRDs already present, skipping install"
    return 0
  fi

  log "Installing cert-manager ${CERT_MANAGER_VERSION}"
  helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --version "${CERT_MANAGER_VERSION}" \
    --set crds.enabled=true \
    --wait --timeout 5m >/dev/null

  log "cert-manager installed"
}

otel_install_operator() {
  if kubectl_cmd get crd instrumentations.opentelemetry.io >/dev/null 2>&1; then
    log "OpenTelemetry Operator CRDs already present, upgrading"
  else
    log "Installing OpenTelemetry Operator ${OTEL_OPERATOR_VERSION}"
  fi

  helm upgrade --install opentelemetry-operator open-telemetry/opentelemetry-operator \
    --namespace "${OTEL_OPERATOR_NAMESPACE}" \
    --create-namespace \
    --version "${OTEL_OPERATOR_VERSION}" \
    --set "manager.collectorImage.repository=otel/opentelemetry-collector-contrib" \
    --wait --timeout 5m >/dev/null

  log "OpenTelemetry Operator ready in ${OTEL_OPERATOR_NAMESPACE}"
}

otel_install_splunk_collector() {
  require_env SPLUNK_O11Y_REALM
  local ingest_token="${SPLUNK_O11Y_INGEST_TOKEN:-${SPLUNK_O11Y_API_TOKEN}}"
  [[ -n "${ingest_token}" ]] || die "SPLUNK_O11Y_INGEST_TOKEN (or SPLUNK_O11Y_API_TOKEN) is required for the collector"

  log "Installing Splunk OTel Collector ${SPLUNK_OTEL_CHART_VERSION} into ${OTEL_COLLECTOR_NAMESPACE}"

  helm upgrade --install splunk-otel-collector splunk-otel-collector-chart/splunk-otel-collector \
    --namespace "${OTEL_COLLECTOR_NAMESPACE}" \
    --create-namespace \
    --version "${SPLUNK_OTEL_CHART_VERSION}" \
    --set "splunkObservability.realm=${SPLUNK_O11Y_REALM}" \
    --set "splunkObservability.accessToken=${ingest_token}" \
    --set "splunkObservability.metricsEnabled=true" \
    --set "splunkObservability.tracesEnabled=true" \
    --set "splunkObservability.logsEnabled=true" \
    --set "clusterName=${OTEL_CLUSTER_NAME:-filaops-demo}" \
    --set "agent.enabled=true" \
    --set "clusterReceiver.enabled=true" \
    --wait --timeout 5m >/dev/null

  log "Splunk OTel Collector ready in ${OTEL_COLLECTOR_NAMESPACE}"
}

otel_wait_ready() {
  local timeout="${1:-120}"
  local elapsed=0

  log "Waiting for collector agent pods in ${OTEL_COLLECTOR_NAMESPACE}..."
  while (( elapsed < timeout )); do
    if kubectl_cmd -n "${OTEL_COLLECTOR_NAMESPACE}" get ds splunk-otel-collector-agent >/dev/null 2>&1; then
      local desired ready
      desired="$(kubectl_cmd -n "${OTEL_COLLECTOR_NAMESPACE}" get ds splunk-otel-collector-agent -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || true)"
      ready="$(kubectl_cmd -n "${OTEL_COLLECTOR_NAMESPACE}" get ds splunk-otel-collector-agent -o jsonpath='{.status.numberReady}' 2>/dev/null || true)"
      desired="${desired:-0}"
      ready="${ready:-0}"
      if [[ "${desired}" -gt 0 && "${desired}" == "${ready}" ]]; then
        log "Collector agent DaemonSet ready (${ready}/${desired})"
        return 0
      fi
    fi
    sleep 5
    elapsed=$((elapsed + 5))
  done

  warn "Timed out waiting for collector agents after ${timeout}s; continuing anyway"
}

otel_install_infra() {
  require_cmd helm
  otel_ensure_helm_repos
  otel_install_cert_manager
  otel_install_operator
  otel_install_splunk_collector
  otel_wait_ready
  log "OTel infrastructure deployment complete"
}

otel_teardown() {
  require_cmd helm
  log "Removing Splunk OTel Collector"
  helm uninstall splunk-otel-collector --namespace "${OTEL_COLLECTOR_NAMESPACE}" 2>/dev/null || true
  kubectl_cmd delete namespace "${OTEL_COLLECTOR_NAMESPACE}" --ignore-not-found 2>/dev/null || true

  log "Removing OpenTelemetry Operator"
  helm uninstall opentelemetry-operator --namespace "${OTEL_OPERATOR_NAMESPACE}" 2>/dev/null || true
  kubectl_cmd delete namespace "${OTEL_OPERATOR_NAMESPACE}" --ignore-not-found 2>/dev/null || true

  log "OTel infrastructure removed (cert-manager left in place)"
}
