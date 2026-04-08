#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

load_demo_env_files() {
  local explicit_env_file="${DEMO_ENV_FILE:-}"
  local env_file

  if [[ -n "${explicit_env_file}" && ! -f "${explicit_env_file}" ]]; then
    printf '[demo][error] DEMO_ENV_FILE not found: %s\n' "${explicit_env_file}" >&2
    exit 1
  fi

  for env_file in "${script_dir}/.env" "${script_dir}/.env.local" "${explicit_env_file}"; do
    [[ -z "${env_file}" || ! -f "${env_file}" ]] && continue
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
  done
}

load_demo_env_files

source "${script_dir}/lib/common.sh"
source "${script_dir}/lib/thousandeyes.sh"
source "${script_dir}/lib/splunk_o11y.sh"
source "${script_dir}/lib/thousandeyes_agent.sh"
source "${script_dir}/lib/otel_infra.sh"
source "${script_dir}/lib/app_deploy.sh"
source "${script_dir}/lib/cilium.sh"

# Support the variable names commonly used in the rest of the repo and lab notes.
: "${SPLUNK_O11Y_REALM:=${SPLUNK_REALM:-}}"
: "${SPLUNK_O11Y_API_TOKEN:=${SPLUNK_ACCESS_TOKEN:-}}"
: "${SPLUNK_O11Y_INGEST_TOKEN:=${SPLUNK_INGEST_TOKEN:-${SPLUNK_ACCESS_TOKEN:-}}}"
: "${THOUSANDEYES_API_TOKEN:=${THOUSANDEYES_BEARER_TOKEN:-}}"
: "${THOUSANDEYES_ACCOUNT_GROUP_ID:=${THOUSANDEYES_DEMO_ACCOUNT_GROUP_ID:-2114135}}"

NAMESPACE="${NAMESPACE:-3dprint}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/demo/3dprint-observability.sh <command>

Turnkey (recommended for first-time setup):
  deploy      Install OTel infra, deploy app, provision all integrations
  teardown    Remove app, integrations, and optionally OTel infra

Demo lifecycle:
  setup       Provision ThousandEyes tests, Splunk dashboards, OTel streams
  baseline    Run healthy baseline load and smoke
  break       Apply reversible deny policy (backend -> order-ingest)
  restore     Remove policy and verify recovery
  cleanup     Remove policy and prune jobs; PURGE_REMOTE_ASSETS=true to delete remote assets
  links       Print current dashboard and handoff URLs

Enterprise Agent:
  agent-install   Deploy repo-managed ThousandEyes enterprise agent
  agent-remove    Remove repo-managed enterprise agent
  agent-status    Show enterprise agent status

Environment loading:
  auto-loads scripts/demo/.env and scripts/demo/.env.local when present
  set DEMO_ENV_FILE=/path/to/private-demo.env to load a separate credentials file

Required environment for `deploy` and `setup`:
  SPLUNK_O11Y_REALM            Splunk Observability realm (e.g. us1)
  SPLUNK_O11Y_API_TOKEN        Splunk API token (dashboards, events)
  SPLUNK_O11Y_INGEST_TOKEN     Splunk ingest token (collector, OTel stream)
  THOUSANDEYES_API_TOKEN        ThousandEyes API bearer token
  FRONTEND_URL                  Public URL of the deployed frontend
  DEMO_ADMIN_EMAIL              Demo admin login email
  DEMO_ADMIN_PASSWORD           Demo admin login password

  Agent IDs (at least one pattern):
    THOUSANDEYES_AGENT_IDS                    all-in-one agent list
    THOUSANDEYES_BROWSER_AGENT_IDS            browser-capable agents
    THOUSANDEYES_HTTP_AGENT_IDS               HTTP/API agents
    THOUSANDEYES_ENTERPRISE_AGENT_ACCOUNT_TOKEN  install in-cluster agent

Optional environment:
  CERT_MANAGER_VERSION          Pin cert-manager Helm chart version
  OTEL_OPERATOR_VERSION         Pin OTel Operator Helm chart version
  SPLUNK_OTEL_CHART_VERSION     Pin Splunk collector Helm chart version
  OTEL_CLUSTER_NAME             Cluster name for collector metadata
  SPLUNK_NETWORK_EXPLORER_URL   Handoff link for Network Explorer
  ISOVALENT_DASHBOARD_URL       Handoff link for Isovalent
  THOUSANDEYES_DASHBOARD_URL    Handoff link for ThousandEyes
  ISOVALENT_DROP_METRIC         Cilium drop metric name (default: cilium_drop_count_total)
  ISOVALENT_FLOW_METRIC         Hubble flow metric name (default: hubble_flows_processed_total)
  KUBECTL_FLAGS                 Extra flags passed to all kubectl calls
  PURGE_REMOTE_ASSETS=true      Delete remote TE/Splunk assets on cleanup
EOF
}

kubectl_cmd() {
  local -a extra_flags=()
  if [[ -n "${KUBECTL_FLAGS:-}" ]]; then
    read -r -a extra_flags <<<"${KUBECTL_FLAGS}"
  fi
  kubectl "${extra_flags[@]}" "$@"
}

ensure_setup_env() {
  ensure_prereqs
  require_env \
    SPLUNK_O11Y_REALM \
    SPLUNK_O11Y_API_TOKEN \
    THOUSANDEYES_API_TOKEN \
    THOUSANDEYES_ACCOUNT_GROUP_ID \
    FRONTEND_URL \
    DEMO_ADMIN_EMAIL \
    DEMO_ADMIN_PASSWORD

  if [[ -z "${THOUSANDEYES_BROWSER_AGENT_IDS:-${THOUSANDEYES_AGENT_IDS:-}}" ]]; then
    die "Missing browser-capable ThousandEyes agent IDs. Set THOUSANDEYES_BROWSER_AGENT_IDS or THOUSANDEYES_AGENT_IDS."
  fi

  if [[ -z "${THOUSANDEYES_HTTP_AGENT_IDS:-${THOUSANDEYES_AGENT_IDS:-}}" ]] \
    && [[ -z "${THOUSANDEYES_API_AGENT_IDS:-${THOUSANDEYES_AGENT_IDS:-}}" ]] \
    && [[ -z "${THOUSANDEYES_ENTERPRISE_AGENT_ACCOUNT_TOKEN:-}" ]] \
    && ! state_get_string "thousandeyes.cluster_agent.id" >/dev/null 2>&1
  then
    die "Missing ThousandEyes HTTP/API agents. Set THOUSANDEYES_AGENT_IDS, THOUSANDEYES_HTTP_AGENT_IDS / THOUSANDEYES_API_AGENT_IDS, or THOUSANDEYES_ENTERPRISE_AGENT_ACCOUNT_TOKEN."
  fi
}

ensure_sfx_env() {
  ensure_prereqs
  require_env SPLUNK_O11Y_REALM SPLUNK_O11Y_API_TOKEN
}

ensure_cluster_env() {
  ensure_prereqs
  require_cmd kubectl
}

assert_cluster_ready() {
  kubectl_cmd -n "${NAMESPACE}" get deploy/backend >/dev/null
  kubectl_cmd -n "${NAMESPACE}" get deploy/order-ingest >/dev/null
}

apply_demo_policy() {
  cilium_apply_demo_policy
}

remove_demo_policy() {
  cilium_remove_demo_policy
}

run_backend_smoke() {
  local run_id="$1"
  local mode="$2"
  local expected_status="$3"
  RUN_ID="${run_id}" MODE="${mode}" EXPECT_ORDER_IMPORT_STATUS="${expected_status}" \
    bash "${repo_root}/k8s/3dprint/run-backend-service-smoke.sh"
}

run_setup() {
  local run_id

  ensure_setup_env
  run_id="$(resolve_run_id reuse)"

  if [[ -n "${THOUSANDEYES_ENTERPRISE_AGENT_ACCOUNT_TOKEN:-}" ]]; then
    log "Installing repo-managed ThousandEyes enterprise agent into the cluster"
    te_agent_install
  fi

  te_seed_existing_test_ids_from_env

  log "Provisioning ThousandEyes tests and Splunk Observability dashboards"
  te_upsert_http_server_test >/dev/null
  if [[ "${THOUSANDEYES_PIN_EXISTING_TRANSACTION_TESTS:-false}" == "true" ]] \
    && [[ -n "${THOUSANDEYES_EXISTING_WEB_TRANSACTION_TEST_ID:-}" ]]; then
    te_pin_test_id_read_only "thousandeyes.tests.web_transaction" "${THOUSANDEYES_EXISTING_WEB_TRANSACTION_TEST_ID}"
  else
    te_upsert_web_transaction_test_optional >/dev/null
  fi

  if [[ "${THOUSANDEYES_PIN_EXISTING_TRANSACTION_TESTS:-false}" == "true" ]] \
    && [[ -n "${THOUSANDEYES_EXISTING_API_TEST_ID:-}" ]]; then
    te_pin_test_id_read_only "thousandeyes.tests.api" "${THOUSANDEYES_EXISTING_API_TEST_ID}"
  else
    te_upsert_api_test_optional >/dev/null
  fi

  te_refresh_demo_test_bindings >/dev/null || true
  te_upsert_o11y_stream >/dev/null
  te_upsert_o11y_trace_stream >/dev/null

  if te_vendor_dashboards_supported; then
    sfx_import_dashboard_package \
      "${repo_root}/scripts/demo/assets/splunk-o11y/thousandeyes-dashboard-package.json" \
      "splunk.packages.vendor_te"
  else
    warn "Skipping the imported ThousandEyes dashboard package because one or more pinned/shared tests are not FilaOps-compatible."
    sfx_cleanup_dashboard_package "splunk.packages.vendor_te"
  fi
  sfx_cache_isovalent_dashboard_links >/dev/null || true
  sfx_demo_dashboards "${run_id}"
  sfx_post_event_marker "setup" "${run_id}" "Provisioned FilaOps cross-observability demo assets."

  printf 'Provisioned demo assets for RUN_ID=%s\n' "${run_id}"
  run_links
}

run_baseline() {
  local run_id

  ensure_sfx_env
  ensure_cluster_env
  assert_cluster_ready

  run_id="$(resolve_run_id new)"
  log "Running baseline flow with RUN_ID=${run_id}"
  sfx_demo_dashboards "${run_id}"
  sfx_post_event_marker "baseline" "${run_id}" "Baseline load and smoke run started."

  bash "${repo_root}/k8s/3dprint/run-seed-loadgen.sh"
  RUN_ID="${run_id}" bash "${repo_root}/k8s/3dprint/run-k6-loadgen.sh"
  RUN_ID="${run_id}" bash "${repo_root}/k8s/3dprint/run-playwright-smoke.sh"
  run_backend_smoke "${run_id}" "full" "200"

  sfx_post_event_marker "baseline-complete" "${run_id}" "Baseline load and smoke run completed successfully."
  printf 'Baseline complete for RUN_ID=%s\n' "${run_id}"
}

run_break() {
  local run_id

  ensure_sfx_env
  ensure_cluster_env
  assert_cluster_ready

  run_id="$(resolve_run_id reuse)"
  apply_demo_policy
  sfx_demo_dashboards "${run_id}"
  sfx_post_event_marker "policy-applied" "${run_id}" "Applied reversible demo policy blocking backend -> order-ingest."
  run_backend_smoke "${run_id}" "order-import-only" "502"
  printf 'Break condition confirmed for RUN_ID=%s\n' "${run_id}"
}

run_restore() {
  local run_id

  ensure_sfx_env
  ensure_cluster_env
  assert_cluster_ready

  run_id="$(resolve_run_id reuse)"
  remove_demo_policy
  sfx_post_event_marker "policy-removed" "${run_id}" "Removed demo deny policy and started recovery verification."
  run_backend_smoke "${run_id}" "order-import-only" "200"
  sfx_demo_dashboards "${run_id}"
  sfx_post_event_marker "restore-complete" "${run_id}" "Order import recovered after policy removal."
  printf 'Restore complete for RUN_ID=%s\n' "${run_id}"
}

run_cleanup() {
  ensure_cluster_env
  remove_demo_policy
  bash "${repo_root}/k8s/3dprint/cleanup-finished-jobs.sh" >/dev/null

  if [[ "${PURGE_REMOTE_ASSETS:-false}" == "true" ]]; then
    ensure_setup_env
    te_cleanup_remote_assets || true
    sfx_cleanup_remote_assets || true
    te_agent_remove || true
    printf '{}\n' > "${demo_state_file}"
    printf 'Cleaned local state and remote observability assets\n'
    return 0
  fi

  state_delete_key "current_run_id" || true
  printf 'Removed demo policy and pruned finished demo jobs\n'
}

run_agent_install() {
  ensure_prereqs
  te_agent_install
  if state_get_string "thousandeyes.cluster_agent.id" >/dev/null 2>&1; then
    printf 'Installed ThousandEyes enterprise agent %s (id=%s)\n' \
      "$(state_get_string "thousandeyes.cluster_agent.name")" \
      "$(state_get_string "thousandeyes.cluster_agent.id")"
  else
    printf 'Installed ThousandEyes enterprise agent deployment %s in namespace %s\n' \
      "$(te_agent_deployment_name)" "$(te_agent_namespace)"
  fi
}

run_agent_remove() {
  te_agent_remove
  printf 'Removed ThousandEyes enterprise agent deployment %s from namespace %s\n' \
    "$(te_agent_deployment_name)" "$(te_agent_namespace)"
}

run_agent_status() {
  te_agent_status
}

ensure_deploy_env() {
  ensure_setup_env
  require_cmd helm
  require_cmd kubectl

  local ingest_token="${SPLUNK_O11Y_INGEST_TOKEN:-${SPLUNK_O11Y_API_TOKEN:-}}"
  if [[ -z "${ingest_token}" ]]; then
    die "SPLUNK_O11Y_INGEST_TOKEN (or SPLUNK_O11Y_API_TOKEN) is required for deploy"
  fi
}

run_deploy() {
  ensure_deploy_env

  log "=== Phase 1: OTel Infrastructure ==="
  otel_install_infra

  log "=== Phase 2: App Deployment ==="
  app_deploy

  log "=== Phase 3: Integrations ==="
  run_setup

  log "=== Phase 3b: Cilium / Hubble ==="
  cilium_ensure_hubble_metrics

  log "=== Deploy complete ==="
}

run_teardown() {
  ensure_prereqs

  log "Cleaning up demo assets and remote integrations"
  PURGE_REMOTE_ASSETS=true run_cleanup || true

  log "Removing app namespace"
  app_teardown || true

  if [[ "${TEARDOWN_OTEL:-false}" == "true" ]]; then
    log "Removing OTel infrastructure"
    otel_teardown || true
  else
    log "OTel infrastructure left in place (set TEARDOWN_OTEL=true to remove)"
  fi

  log "Teardown complete"
}

run_links() {
  local run_id
  ensure_prereqs
  require_env SPLUNK_O11Y_REALM
  run_id="$(resolve_run_id reuse)"
  printf 'RUN_ID: %s\n' "${run_id}"
  sfx_print_links
  te_print_links
}

main() {
  local command="${1:-}"

  case "${command}" in
    deploy)
      run_deploy
      ;;
    teardown)
      run_teardown
      ;;
    setup)
      run_setup
      ;;
    baseline)
      run_baseline
      ;;
    break)
      run_break
      ;;
    restore)
      run_restore
      ;;
    cleanup)
      run_cleanup
      ;;
    links)
      run_links
      ;;
    agent-install)
      run_agent_install
      ;;
    agent-remove)
      run_agent_remove
      ;;
    agent-status)
      run_agent_status
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      usage
      die "Unknown command: ${command}"
      ;;
  esac
}

main "$@"
