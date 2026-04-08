#!/usr/bin/env bash

set -euo pipefail

te_last_http_code=""
te_last_response_body=""

te_api_base_url() {
  printf '%s' "${THOUSANDEYES_API_BASE_URL:-https://api.thousandeyes.com/v7}"
}

te_agent_ids_json_for_role() {
  local role="$1"
  local var_name
  local raw_csv=""
  local raw_json='[]'
  local cluster_agent_id=""

  case "${role}" in
    http)
      var_name="THOUSANDEYES_HTTP_AGENT_IDS"
      ;;
    browser)
      var_name="THOUSANDEYES_BROWSER_AGENT_IDS"
      ;;
    api)
      var_name="THOUSANDEYES_API_AGENT_IDS"
      ;;
    *)
      die "Unsupported ThousandEyes agent role: ${role}"
      ;;
  esac

  raw_csv="${!var_name:-${THOUSANDEYES_AGENT_IDS:-}}"
  if [[ -n "${raw_csv}" ]]; then
    raw_json="$(json_array_from_csv "${raw_csv}")"
  fi

  if [[ "${role}" != "browser" ]] && cluster_agent_id="$(state_get_string "thousandeyes.cluster_agent.id" 2>/dev/null)"; then
    raw_json="$(json_append_string_if_missing "${raw_json}" "${cluster_agent_id}")"
  fi

  raw_json="$(json_unique_strings "${raw_json}")"
  jq -e 'length > 0' >/dev/null <<<"${raw_json}" || die \
    "No ThousandEyes agent IDs resolved for ${role}. Set ${var_name} or THOUSANDEYES_AGENT_IDS."

  jq -cn --argjson agents "${raw_json}" '$agents | map({agentId: .})'
}

te_request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local url
  local response_file
  local http_code

  url="$(te_api_base_url)${path}"
  response_file="$(mktemp)"
  if [[ -n "${body}" ]]; then
    http_code="$(curl -sS -o "${response_file}" -w '%{http_code}' \
      -X "${method}" \
      -H "Authorization: Bearer ${THOUSANDEYES_API_TOKEN}" \
      -H 'Content-Type: application/json' \
      "${url}" \
      -d "${body}")"
  else
    http_code="$(curl -sS -o "${response_file}" -w '%{http_code}' \
      -X "${method}" \
      -H "Authorization: Bearer ${THOUSANDEYES_API_TOKEN}" \
      "${url}")"
  fi

  te_last_http_code="${http_code}"
  te_last_response_body="$(cat "${response_file}")"

  if [[ ! "${http_code}" =~ ^2 ]]; then
    warn "ThousandEyes ${method} ${path} returned ${http_code}"
    printf '%s' "${te_last_response_body}" >&2
    rm -f "${response_file}"
    return 1
  fi

  printf '%s' "${te_last_response_body}"
  rm -f "${response_file}"
}

te_delete() {
  local path="$1"
  local url
  url="$(te_api_base_url)${path}"
  curl -sS -X DELETE -H "Authorization: Bearer ${THOUSANDEYES_API_TOKEN}" "${url}" >/dev/null
}

te_get_test_json_by_id() {
  local type="$1"
  local test_id="$2"

  [[ -n "${test_id}" ]] || return 1
  te_request GET "/tests/${type}/${test_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}"
}

te_url_matches_prefix() {
  local actual_url="${1:-}"
  local expected_prefix="${2:-}"
  local normalized_actual="${actual_url%/}"
  local normalized_expected="${expected_prefix%/}"

  [[ -n "${normalized_actual}" && -n "${normalized_expected}" && "${normalized_actual}" == "${normalized_expected}"* ]]
}

te_refresh_test_binding() {
  local state_prefix="$1"
  local type="$2"
  local expected_name="$3"
  local expected_url_prefix="${4:-}"
  local test_id=""
  local test_json=""
  local actual_name=""
  local actual_url=""
  local compatible="false"

  if ! test_id="$(state_get_string "${state_prefix}.id" 2>/dev/null)"; then
    state_set_string "${state_prefix}.compatible" "false"
    return 1
  fi

  if ! test_json="$(te_get_test_json_by_id "${type}" "${test_id}")"; then
    state_set_string "${state_prefix}.compatible" "false"
    return 1
  fi

  actual_name="$(jq -r '.testName // ""' <<<"${test_json}")"
  actual_url="$(jq -r '.url // ""' <<<"${test_json}")"

  state_set_string "${state_prefix}.resolved_name" "${actual_name}"
  state_set_string "${state_prefix}.resolved_url" "${actual_url}"

  if [[ "${actual_name}" == "${expected_name}" ]] || te_url_matches_prefix "${actual_url}" "${expected_url_prefix}"; then
    compatible="true"
  fi

  state_set_string "${state_prefix}.compatible" "${compatible}"

  if [[ "${compatible}" != "true" ]]; then
    warn "ThousandEyes ${type} test ${test_id} (${actual_name}) does not match the FilaOps demo target ${expected_url_prefix}; related dashboards will be skipped."
  fi

  [[ "${compatible}" == "true" ]]
}

te_refresh_demo_test_bindings() {
  local supported="true"

  te_refresh_test_binding \
    "thousandeyes.tests.http_server" \
    "http-server" \
    "FilaOps Demo - Frontend HTTP" \
    "$(safe_frontend_url)" || supported="false"

  te_refresh_test_binding \
    "thousandeyes.tests.web_transaction" \
    "web-transactions" \
    "FilaOps Demo - Admin Browser" \
    "$(safe_frontend_url)/admin" || supported="false"

  te_refresh_test_binding \
    "thousandeyes.tests.api" \
    "api" \
    "FilaOps Demo - Admin API" \
    "$(safe_api_base_url)" || supported="false"

  state_set_string "thousandeyes.vendor_dashboards_supported" "${supported}"
  [[ "${supported}" == "true" ]]
}

te_vendor_dashboards_supported() {
  [[ "$(state_get_string "thousandeyes.vendor_dashboards_supported" 2>/dev/null || printf 'false')" == "true" ]]
}

te_usage_limit_error() {
  [[ "${te_last_http_code:-}" == "400" ]] && grep -qi 'usage limit' <<<"${te_last_response_body:-}"
}

te_seed_existing_test_ids_from_env() {
  if [[ -n "${THOUSANDEYES_EXISTING_HTTP_SERVER_TEST_ID:-}" ]]; then
    state_set_string "thousandeyes.tests.http_server.id" "${THOUSANDEYES_EXISTING_HTTP_SERVER_TEST_ID}"
  fi
  if [[ -n "${THOUSANDEYES_EXISTING_WEB_TRANSACTION_TEST_ID:-}" ]]; then
    state_set_string "thousandeyes.tests.web_transaction.id" "${THOUSANDEYES_EXISTING_WEB_TRANSACTION_TEST_ID}"
  fi
  if [[ -n "${THOUSANDEYES_EXISTING_API_TEST_ID:-}" ]]; then
    state_set_string "thousandeyes.tests.api.id" "${THOUSANDEYES_EXISTING_API_TEST_ID}"
  fi
}

te_pin_test_id_read_only() {
  local state_prefix="$1"
  local test_id="$2"

  [[ -n "${test_id}" ]] || return 1
  state_set_string "${state_prefix}.id" "${test_id}"
  state_set_string "${state_prefix}.skipped_reason" "pinned existing"
}

te_find_test_id() {
  local type="$1"
  local test_name="$2"
  local tests_json

  tests_json="$(te_request GET "/tests?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")"
  jq -r \
    --arg type "${type}" \
    --arg name "${test_name}" \
    '.tests[] | select(.type == $type and .testName == $name) | .testId' \
    <<<"${tests_json}" | head -n 1
}

te_upsert_test() {
  local state_prefix="$1"
  local type="$2"
  local test_name="$3"
  local payload="$4"
  local test_id=""
  local response=""

  if test_id="$(state_get_string "${state_prefix}.id" 2>/dev/null)"; then
    :
  else
    test_id="$(te_find_test_id "${type}" "${test_name}" || true)"
    if [[ -n "${test_id}" ]]; then
      state_set_string "${state_prefix}.id" "${test_id}"
    fi
  fi

  if [[ -n "${test_id}" ]]; then
    response="$(te_request PUT "/tests/${type}/${test_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" "${payload}")"
  else
    response="$(te_request POST "/tests/${type}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" "${payload}")"
    test_id="$(jq -r '.testId // .id' <<<"${response}")"
    state_set_string "${state_prefix}.id" "${test_id}"
  fi

  state_set_string "${state_prefix}.name" "${test_name}"
  printf '%s' "${test_id:-$(jq -r '.testId // .id' <<<"${response}")}"
}

te_upsert_http_server_test() {
  local test_name="FilaOps Demo - Frontend HTTP"
  local payload

  payload="$(jq -cn \
    --arg name "${test_name}" \
    --arg url "$(safe_frontend_url)/" \
    --argjson agents "$(te_agent_ids_json_for_role http)" '
    {
      testName: $name,
      url: $url,
      interval: 300,
      agents: $agents,
      enabled: true,
      alertsEnabled: false,
      followRedirects: true,
      verifyCertificate: true,
      networkMeasurements: true,
      bgpMeasurements: true,
      distributedTracing: true,
      desiredStatusCode: "200"
    }')"

  te_upsert_test "thousandeyes.tests.http_server" "http-server" "${test_name}" "${payload}"
}

te_upsert_web_transaction_test() {
  local test_name="FilaOps Demo - Admin Browser"
  local transaction_script
  local payload

  transaction_script="$(replace_template_tokens \
    "${demo_assets_root}/thousandeyes/browser-login-dashboard.js.tpl" \
    "__FRONTEND_URL__=$(safe_frontend_url)" \
    "__ADMIN_EMAIL__=${DEMO_ADMIN_EMAIL}" \
    "__ADMIN_PASSWORD__=${DEMO_ADMIN_PASSWORD}")"

  payload="$(jq -cn \
    --arg name "${test_name}" \
    --arg url "$(safe_frontend_url)/admin/login" \
    --arg script "${transaction_script}" \
    --argjson agents "$(te_agent_ids_json_for_role browser)" '
    {
      testName: $name,
      url: $url,
      interval: 300,
      targetTime: 10,
      timeLimit: 60,
      agents: $agents,
      enabled: true,
      alertsEnabled: false,
      followRedirects: true,
      verifyCertificate: true,
      networkMeasurements: true,
      bgpMeasurements: true,
      transactionScript: $script
    }')"

  te_upsert_test "thousandeyes.tests.web_transaction" "web-transactions" "${test_name}" "${payload}"
}

te_mark_optional_test_skipped() {
  local state_prefix="$1"
  local type="$2"
  local test_name="$3"
  local existing_test_id=""

  existing_test_id="$(te_find_test_id "${type}" "${test_name}" || true)"
  if [[ -n "${existing_test_id}" ]]; then
    state_set_string "${state_prefix}.id" "${existing_test_id}"
    state_set_string "${state_prefix}.name" "${test_name}"
  else
    state_delete_key "${state_prefix}.id" || true
    state_delete_key "${state_prefix}.name" || true
  fi

  state_set_string "${state_prefix}.skipped_reason" "usage limit"
}

te_upsert_web_transaction_test_optional() {
  local test_name="FilaOps Demo - Admin Browser"

  if te_upsert_web_transaction_test; then
    state_delete_key "thousandeyes.tests.web_transaction.skipped_reason" || true
    return 0
  fi

  if te_usage_limit_error; then
    te_mark_optional_test_skipped "thousandeyes.tests.web_transaction" "web-transactions" "${test_name}"
    warn "Skipping ThousandEyes browser transaction provisioning because account group ${THOUSANDEYES_ACCOUNT_GROUP_ID} has reached its web transaction usage limit."
    return 0
  fi

  return 1
}

te_upsert_api_test() {
  local test_name="FilaOps Demo - Admin API"
  local api_base
  local payload

  api_base="$(safe_api_base_url)"
  payload="$(jq -cn \
    --arg name "${test_name}" \
    --arg url "${api_base}/health" \
    --arg loginUrl "${api_base}/auth/login" \
    --arg meUrl "${api_base}/auth/me" \
    --arg dashboardUrl "${api_base}/admin/dashboard/summary" \
    --arg adminEmail "${DEMO_ADMIN_EMAIL}" \
    --arg adminPassword "${DEMO_ADMIN_PASSWORD}" \
    --argjson agents "$(te_agent_ids_json_for_role api)" '
    {
      testName: $name,
      url: $url,
      interval: 300,
      targetTime: 10,
      timeLimit: 60,
      agents: $agents,
      enabled: true,
      alertsEnabled: false,
      followRedirects: true,
      verifyCertificate: true,
      networkMeasurements: true,
      distributedTracing: true,
      predefinedVariables: [
        {name: "admin_email", value: $adminEmail},
        {name: "admin_password", value: $adminPassword}
      ],
      requests: [
        {
          name: "login",
          method: "post",
          url: $loginUrl,
          headers: [
            {key: "Content-Type", value: "application/x-www-form-urlencoded"}
          ],
          body: "username={{admin_email}}&password={{admin_password}}",
          assertions: [
            {name: "status-code", operator: "is", value: "200"},
            {name: "response-body", operator: "includes", value: "Login successful"}
          ],
          collectApiResponse: true,
          verifyCertificate: true
        },
        {
          name: "auth-me",
          method: "get",
          url: $meUrl,
          assertions: [
            {name: "status-code", operator: "is", value: "200"},
            {name: "response-body", operator: "includes", value: $adminEmail}
          ],
          collectApiResponse: true,
          verifyCertificate: true
        },
        {
          name: "dashboard-summary",
          method: "get",
          url: $dashboardUrl,
          assertions: [
            {name: "status-code", operator: "is", value: "200"}
          ],
          collectApiResponse: true,
          verifyCertificate: true
        }
      ]
    }')"

  te_upsert_test "thousandeyes.tests.api" "api" "${test_name}" "${payload}"
}

te_upsert_api_test_optional() {
  local test_name="FilaOps Demo - Admin API"

  if te_upsert_api_test; then
    state_delete_key "thousandeyes.tests.api.skipped_reason" || true
    return 0
  fi

  if te_usage_limit_error; then
    te_mark_optional_test_skipped "thousandeyes.tests.api" "api" "${test_name}"
    warn "Skipping ThousandEyes API test provisioning because account group ${THOUSANDEYES_ACCOUNT_GROUP_ID} has reached its transaction usage limit."
    return 0
  fi

  return 1
}

te_upsert_o11y_stream() {
  local stream_id=""
  local response=""
  local test_matches='[]'
  local http_test_id=""
  local web_test_id=""
  local api_test_id=""
  local payload

  if http_test_id="$(state_get_string "thousandeyes.tests.http_server.id" 2>/dev/null)"; then :; else http_test_id=""; fi
  if web_test_id="$(state_get_string "thousandeyes.tests.web_transaction.id" 2>/dev/null)"; then :; else web_test_id=""; fi
  if api_test_id="$(state_get_string "thousandeyes.tests.api.id" 2>/dev/null)"; then :; else api_test_id=""; fi

  if [[ -n "${http_test_id}" ]]; then
    test_matches="$(jq -cn --argjson tests "${test_matches}" --arg id "${http_test_id}" '$tests + [{id: $id, domain: "cea"}]')"
  fi
  if [[ -n "${web_test_id}" ]]; then
    test_matches="$(jq -cn --argjson tests "${test_matches}" --arg id "${web_test_id}" '$tests + [{id: $id, domain: "cea"}]')"
  fi
  if [[ -n "${api_test_id}" ]]; then
    test_matches="$(jq -cn --argjson tests "${test_matches}" --arg id "${api_test_id}" '$tests + [{id: $id, domain: "cea"}]')"
  fi

  payload="$(jq -cn \
    --arg endpoint "https://ingest.${SPLUNK_O11Y_REALM}.signalfx.com/v2/datapoint/otlp" \
    --arg token "${SPLUNK_O11Y_INGEST_TOKEN:-${SPLUNK_O11Y_API_TOKEN}}" \
    --argjson tests "${test_matches}" '
    {
      type: "opentelemetry",
      signal: "metric",
      endpointType: "http",
      streamEndpointUrl: $endpoint,
      dataModelVersion: "v2",
      enabled: true,
      customHeaders: {
        "X-SF-Token": $token
      },
      filters: {
        testTypes: {
          values: ["http-server", "web-transactions", "api"]
        }
      },
      testMatch: $tests
    }')"

  if stream_id="$(state_get_string "thousandeyes.streams.o11y_metrics.id" 2>/dev/null)"; then
    response="$(te_request PUT "/streams/${stream_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" "${payload}")"
  else
    response="$(te_request POST "/streams?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" "${payload}")"
    stream_id="$(jq -r '.id' <<<"${response}")"
    state_set_string "thousandeyes.streams.o11y_metrics.id" "${stream_id}"
  fi

  printf '%s' "${stream_id:-$(jq -r '.id' <<<"${response}")}"
}

te_upsert_o11y_trace_stream() {
  local stream_id=""
  local response=""
  local test_matches='[]'
  local http_test_id=""
  local web_test_id=""
  local api_test_id=""
  local payload

  if http_test_id="$(state_get_string "thousandeyes.tests.http_server.id" 2>/dev/null)"; then :; else http_test_id=""; fi
  if web_test_id="$(state_get_string "thousandeyes.tests.web_transaction.id" 2>/dev/null)"; then :; else web_test_id=""; fi
  if api_test_id="$(state_get_string "thousandeyes.tests.api.id" 2>/dev/null)"; then :; else api_test_id=""; fi

  if [[ -n "${http_test_id}" ]]; then
    test_matches="$(jq -cn --argjson tests "${test_matches}" --arg id "${http_test_id}" '$tests + [{id: $id, domain: "cea"}]')"
  fi
  if [[ -n "${web_test_id}" ]]; then
    test_matches="$(jq -cn --argjson tests "${test_matches}" --arg id "${web_test_id}" '$tests + [{id: $id, domain: "cea"}]')"
  fi
  if [[ -n "${api_test_id}" ]]; then
    test_matches="$(jq -cn --argjson tests "${test_matches}" --arg id "${api_test_id}" '$tests + [{id: $id, domain: "cea"}]')"
  fi

  payload="$(jq -cn \
    --arg endpoint "https://ingest.${SPLUNK_O11Y_REALM}.signalfx.com/v2/trace/otlp" \
    --arg token "${SPLUNK_O11Y_INGEST_TOKEN:-${SPLUNK_O11Y_API_TOKEN}}" \
    --argjson tests "${test_matches}" '
    {
      type: "opentelemetry",
      signal: "trace",
      endpointType: "http",
      streamEndpointUrl: $endpoint,
      dataModelVersion: "v2",
      enabled: true,
      customHeaders: {
        "X-SF-Token": $token
      },
      filters: {
        testTypes: {
          values: ["http-server", "web-transactions", "api"]
        }
      },
      testMatch: $tests
    }')"

  if stream_id="$(state_get_string "thousandeyes.streams.o11y_traces.id" 2>/dev/null)"; then
    response="$(te_request PUT "/streams/${stream_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" "${payload}")"
  else
    if response="$(te_request POST "/streams?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" "${payload}")"; then
      stream_id="$(jq -r '.id' <<<"${response}")"
      state_set_string "thousandeyes.streams.o11y_traces.id" "${stream_id}"
    else
      warn "ThousandEyes trace stream creation returned an error; the account may not support trace signal. Continuing with metrics only."
      return 0
    fi
  fi

  printf '%s' "${stream_id:-$(jq -r '.id' <<<"${response}")}"
}

te_print_links() {
  local key
  local test_id
  printf 'ThousandEyes tests\n'
  for key in http_server web_transaction api; do
    if test_id="$(state_get_string "thousandeyes.tests.${key}.id" 2>/dev/null)"; then
      printf '  %-18s %s\n' "${key}" "${test_id}"
    fi
  done
  if test_id="$(state_get_string "thousandeyes.streams.o11y_metrics.id" 2>/dev/null)"; then
    printf '  %-18s %s\n' "metric-stream" "${test_id}"
  fi
  if test_id="$(state_get_string "thousandeyes.streams.o11y_traces.id" 2>/dev/null)"; then
    printf '  %-18s %s\n' "trace-stream" "${test_id}"
  fi
  if test_id="$(state_get_string "thousandeyes.cluster_agent.id" 2>/dev/null)"; then
    printf '  %-18s %s (%s)\n' \
      "cluster-agent" \
      "${test_id}" \
      "$(state_get_string "thousandeyes.cluster_agent.name" 2>/dev/null || printf 'unknown')"
  fi
}

te_cleanup_remote_assets() {
  local test_id
  local stream_id

  if stream_id="$(state_get_string "thousandeyes.streams.o11y_traces.id" 2>/dev/null)"; then
    te_delete "/streams/${stream_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" || true
  fi
  if stream_id="$(state_get_string "thousandeyes.streams.o11y_metrics.id" 2>/dev/null)"; then
    te_delete "/streams/${stream_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" || true
  fi

  if test_id="$(state_get_string "thousandeyes.tests.api.id" 2>/dev/null)"; then
    te_delete "/tests/api/${test_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" || true
  fi
  if test_id="$(state_get_string "thousandeyes.tests.web_transaction.id" 2>/dev/null)"; then
    te_delete "/tests/web-transactions/${test_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" || true
  fi
  if test_id="$(state_get_string "thousandeyes.tests.http_server.id" 2>/dev/null)"; then
    te_delete "/tests/http-server/${test_id}?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}" || true
  fi
}

te_find_agent_id_by_name() {
  local agent_name="$1"
  local agents_json

  agents_json="$(te_request GET "/agents?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")"
  jq -r --arg name "${agent_name}" '
    .agents[]
    | select(.agentName == $name)
    | .agentId
  ' <<<"${agents_json}" | head -n 1
}
