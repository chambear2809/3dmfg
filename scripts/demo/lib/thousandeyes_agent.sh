#!/usr/bin/env bash

set -euo pipefail

te_agent_namespace() {
  printf '%s' "${THOUSANDEYES_ENTERPRISE_AGENT_NAMESPACE:-thousandeyes}"
}

te_agent_name() {
  printf '%s' "${THOUSANDEYES_ENTERPRISE_AGENT_NAME:-filaops-demo-ea}"
}

te_agent_deployment_name() {
  printf '%s' "$(slugify "$(te_agent_name)")"
}

te_agent_secret_name() {
  printf '%s-token' "$(te_agent_deployment_name)"
}

te_agent_pvc_name() {
  printf '%s-state' "$(te_agent_deployment_name)"
}

te_agent_storage_class_block() {
  local storage_class="${THOUSANDEYES_ENTERPRISE_AGENT_STORAGE_CLASS:-gp2}"
  if [[ -z "${storage_class}" ]]; then
    printf ''
    return 0
  fi
  printf '  storageClassName: %s\n' "${storage_class}"
}

te_agent_manifest() {
  replace_template_tokens \
    "${demo_assets_root}/thousandeyes/enterprise-agent.yaml.tpl" \
    "__NAMESPACE__=$(te_agent_namespace)" \
    "__SECRET_NAME__=$(te_agent_secret_name)" \
    "__ACCOUNT_TOKEN__=${THOUSANDEYES_ENTERPRISE_AGENT_ACCOUNT_TOKEN}" \
    "__PVC_NAME__=$(te_agent_pvc_name)" \
    "__STORAGE_CLASS_BLOCK__=$(te_agent_storage_class_block)" \
    "__STORAGE_SIZE__=${THOUSANDEYES_ENTERPRISE_AGENT_STORAGE_SIZE:-20Gi}" \
    "__DEPLOYMENT_NAME__=$(te_agent_deployment_name)" \
    "__HOSTNAME__=$(te_agent_name)" \
    "__IMAGE__=${THOUSANDEYES_ENTERPRISE_AGENT_IMAGE:-thousandeyes/enterprise-agent}" \
    "__TEAGENT_INET__=${THOUSANDEYES_ENTERPRISE_AGENT_INET:-4}" \
    "__CPU_REQUEST__=${THOUSANDEYES_ENTERPRISE_AGENT_CPU_REQUEST:-500m}" \
    "__MEMORY_REQUEST__=${THOUSANDEYES_ENTERPRISE_AGENT_MEMORY_REQUEST:-2Gi}" \
    "__MEMORY_LIMIT__=${THOUSANDEYES_ENTERPRISE_AGENT_MEMORY_LIMIT:-2Gi}"
}

te_agent_wait_for_rollout() {
  kubectl_cmd -n "$(te_agent_namespace)" rollout status "deploy/$(te_agent_deployment_name)" --timeout="${THOUSANDEYES_ENTERPRISE_AGENT_ROLLOUT_TIMEOUT:-10m}"
}

te_agent_wait_for_registration() {
  local agent_name
  local attempts=30
  local sleep_seconds=10
  local current_attempt=1
  local agent_id=""

  agent_name="$(te_agent_name)"
  while (( current_attempt <= attempts )); do
    if agent_id="$(te_find_agent_id_by_name "${agent_name}" 2>/dev/null)" && [[ -n "${agent_id}" ]]; then
      state_set_string "thousandeyes.cluster_agent.id" "${agent_id}"
      state_set_string "thousandeyes.cluster_agent.name" "${agent_name}"
      state_set_string "thousandeyes.cluster_agent.namespace" "$(te_agent_namespace)"
      printf '%s' "${agent_id}"
      return 0
    fi
    sleep "${sleep_seconds}"
    current_attempt=$((current_attempt + 1))
  done

  warn "Timed out waiting for ThousandEyes enterprise agent ${agent_name} to register."
  return 1
}

te_agent_install() {
  require_env THOUSANDEYES_ENTERPRISE_AGENT_ACCOUNT_TOKEN
  require_env THOUSANDEYES_API_TOKEN THOUSANDEYES_ACCOUNT_GROUP_ID
  ensure_cluster_env

  kubectl_cmd get namespace "$(te_agent_namespace)" >/dev/null 2>&1 || \
    kubectl_cmd create namespace "$(te_agent_namespace)" >/dev/null

  te_agent_manifest | kubectl_cmd apply -f - >/dev/null
  te_agent_wait_for_rollout >/dev/null
  te_agent_wait_for_registration >/dev/null || true
}

te_agent_remove() {
  ensure_cluster_env
  kubectl_cmd -n "$(te_agent_namespace)" delete deploy "$(te_agent_deployment_name)" --ignore-not-found >/dev/null 2>&1 || true
  kubectl_cmd -n "$(te_agent_namespace)" delete pvc "$(te_agent_pvc_name)" --ignore-not-found >/dev/null 2>&1 || true
  kubectl_cmd -n "$(te_agent_namespace)" delete secret "$(te_agent_secret_name)" --ignore-not-found >/dev/null 2>&1 || true
  state_delete_key "thousandeyes.cluster_agent" || true
}

te_agent_status() {
  local namespace
  local deployment

  namespace="$(te_agent_namespace)"
  deployment="$(te_agent_deployment_name)"
  if kubectl_cmd -n "${namespace}" get deploy "${deployment}" >/dev/null 2>&1; then
    kubectl_cmd -n "${namespace}" get deploy "${deployment}"
    kubectl_cmd -n "${namespace}" get pods -l "app.kubernetes.io/instance=${deployment}"
  else
    warn "No ThousandEyes enterprise agent deployment found in namespace ${namespace}"
  fi

  if state_get_string "thousandeyes.cluster_agent.id" >/dev/null 2>&1; then
    printf 'Registered agent ID: %s\n' "$(state_get_string "thousandeyes.cluster_agent.id")"
    printf 'Agent name: %s\n' "$(state_get_string "thousandeyes.cluster_agent.name")"
  fi
}
