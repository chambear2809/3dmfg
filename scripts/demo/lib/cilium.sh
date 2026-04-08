#!/usr/bin/env bash

set -euo pipefail

CILIUM_DETECTED=""

cilium_detect() {
  if kubectl_cmd get crd ciliumnetworkpolicies.cilium.io >/dev/null 2>&1; then
    CILIUM_DETECTED="true"
    state_set_string "cluster.cilium_detected" "true"
    return 0
  fi
  CILIUM_DETECTED=""
  state_set_string "cluster.cilium_detected" "false"
  return 1
}

cilium_is_detected() {
  [[ "${CILIUM_DETECTED}" == "true" ]]
}

cilium_hubble_metrics_endpoint() {
  local namespace="${1:-kube-system}"
  local svc_name
  for svc_name in hubble-metrics hubble-peer; do
    if kubectl_cmd -n "${namespace}" get svc "${svc_name}" >/dev/null 2>&1; then
      printf '%s.%s.svc:9965' "${svc_name}" "${namespace}"
      return 0
    fi
  done
  return 1
}

cilium_ensure_hubble_metrics() {
  require_cmd helm

  if ! cilium_detect; then
    warn "Cilium not detected; skipping Hubble metrics configuration"
    return 0
  fi

  log "Cilium detected on cluster"

  local hubble_endpoint=""
  hubble_endpoint="$(cilium_hubble_metrics_endpoint "kube-system" 2>/dev/null || true)"
  if [[ -z "${hubble_endpoint}" ]]; then
    warn "Hubble metrics service not found in kube-system; Hubble may not be enabled. Skipping Prometheus scrape configuration."
    warn "Enable Hubble metrics on your Cilium install for full policy-impact dashboards."
    return 0
  fi

  log "Found Hubble metrics endpoint at ${hubble_endpoint}"

  local collector_ns="${OTEL_COLLECTOR_NAMESPACE:-otel-splunk}"
  if ! helm status splunk-otel-collector --namespace "${collector_ns}" >/dev/null 2>&1; then
    warn "Splunk OTel Collector Helm release not found in ${collector_ns}; cannot auto-configure Hubble scraping"
    return 0
  fi

  log "Patching Splunk OTel Collector to scrape Hubble metrics"
  local values_file
  values_file="$(mktemp)"
  cat > "${values_file}" <<YAML
agent:
  config:
    receivers:
      prometheus/hubble:
        config:
          scrape_configs:
            - job_name: hubble
              scrape_interval: 30s
              static_configs:
                - targets:
                    - "${hubble_endpoint}"
              metric_relabel_configs:
                - source_labels: [__name__]
                  regex: "hubble_.*|cilium_.*"
                  action: keep
    service:
      pipelines:
        metrics/hubble:
          receivers: [prometheus/hubble]
          processors: [memory_limiter, batch, resourcedetection]
          exporters: [signalfx]
YAML

  helm upgrade splunk-otel-collector splunk-otel-collector-chart/splunk-otel-collector \
    --namespace "${collector_ns}" \
    --reuse-values \
    --values "${values_file}" \
    --wait --timeout 3m >/dev/null 2>&1 || {
      warn "Failed to patch collector with Hubble scrape config; Hubble metrics may need manual configuration"
      rm -f "${values_file}"
      return 0
    }

  rm -f "${values_file}"
  state_set_string "cluster.hubble_scraping" "true"
  log "Collector patched to scrape Hubble metrics from ${hubble_endpoint}"
}

cilium_apply_demo_policy() {
  local manifest
  if cilium_detect; then
    manifest="${repo_root}/k8s/3dprint/policies/order-ingest-deny.cnp.yaml"
    state_set_string "cluster.policy_type" "cilium"
    log "Applying Cilium deny policy for backend -> order-ingest"
  else
    manifest="${repo_root}/k8s/3dprint/policies/order-ingest-deny.netpol.yaml"
    state_set_string "cluster.policy_type" "networkpolicy"
    warn "Cilium CRD not present; applying a broader NetworkPolicy fallback that isolates order-ingest ingress."
  fi

  kubectl_cmd -n "${NAMESPACE}" apply -f "${manifest}" >/dev/null
}

cilium_remove_demo_policy() {
  kubectl_cmd -n "${NAMESPACE}" delete -f "${repo_root}/k8s/3dprint/policies/order-ingest-deny.cnp.yaml" --ignore-not-found >/dev/null 2>&1 || true
  kubectl_cmd -n "${NAMESPACE}" delete -f "${repo_root}/k8s/3dprint/policies/order-ingest-deny.netpol.yaml" --ignore-not-found >/dev/null 2>&1 || true
  state_delete_key "cluster.policy_type" || true
}
