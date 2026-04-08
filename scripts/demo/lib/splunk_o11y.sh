#!/usr/bin/env bash

set -euo pipefail

sfx_api_base_url() {
  printf 'https://api.%s.signalfx.com' "${SPLUNK_O11Y_REALM}"
}

sfx_ingest_base_url() {
  printf 'https://ingest.%s.signalfx.com' "${SPLUNK_O11Y_REALM}"
}

sfx_ingest_token() {
  printf '%s' "${SPLUNK_O11Y_INGEST_TOKEN:-${SPLUNK_O11Y_API_TOKEN}}"
}

sfx_dashboard_url() {
  local dashboard_id="$1"
  printf 'https://app.%s.signalfx.com/#/dashboard/%s' "${SPLUNK_O11Y_REALM}" "${dashboard_id}"
}

sfx_cache_isovalent_dashboard_links() {
  local groups_json=""
  local cilium_group_id=""
  local hubble_group_id=""
  local cilium_group_json=""
  local hubble_group_json=""
  local cilium_dashboard_id=""
  local hubble_dashboard_id=""
  local dashboard_id=""
  local dashboard_json=""
  local dashboard_name=""

  if ! groups_json="$(sfx_request GET "/v2/dashboardgroup?limit=200")"; then
    return 0
  fi

  cilium_group_id="$(jq -r '.results[]? | select(.name == "Cilium by Isovalent") | .id' <<<"${groups_json}" | head -n 1)"
  hubble_group_id="$(jq -r '.results[]? | select(.name == "Hubble by Isovalent") | .id' <<<"${groups_json}" | head -n 1)"

  state_delete_key "splunk.isovalent.dashboard_urls" || true

  if [[ -n "${cilium_group_id}" ]]; then
    cilium_group_json="$(sfx_request GET "/v2/dashboardgroup/${cilium_group_id}" || true)"
    while IFS= read -r dashboard_id; do
      [[ -z "${dashboard_id}" ]] && continue
      dashboard_json="$(sfx_request GET "/v2/dashboard/${dashboard_id}" || true)"
      [[ -n "${dashboard_json}" ]] || continue
      dashboard_name="$(jq -r '.name // ""' <<<"${dashboard_json}")"
      if [[ "${dashboard_name}" == "Policy Verdicts" ]]; then
        cilium_dashboard_id="${dashboard_id}"
        break
      fi
    done < <(jq -r '.dashboards[]?' <<<"${cilium_group_json}")
  fi

  if [[ -n "${hubble_group_id}" ]]; then
    hubble_group_json="$(sfx_request GET "/v2/dashboardgroup/${hubble_group_id}" || true)"
    while IFS= read -r dashboard_id; do
      [[ -z "${dashboard_id}" ]] && continue
      dashboard_json="$(sfx_request GET "/v2/dashboard/${dashboard_id}" || true)"
      [[ -n "${dashboard_json}" ]] || continue
      dashboard_name="$(jq -r '.name // ""' <<<"${dashboard_json}")"
      if [[ "${dashboard_name}" == "Network Overview" ]]; then
        hubble_dashboard_id="${dashboard_id}"
        break
      fi
    done < <(jq -r '.dashboards[]?' <<<"${hubble_group_json}")
  fi

  if [[ -n "${cilium_dashboard_id}" ]]; then
    state_set_string "splunk.isovalent.dashboard_urls.cilium_policy_verdicts" "$(sfx_dashboard_url "${cilium_dashboard_id}")"
  fi

  if [[ -n "${hubble_dashboard_id}" ]]; then
    state_set_string "splunk.isovalent.dashboard_urls.hubble_network_overview" "$(sfx_dashboard_url "${hubble_dashboard_id}")"
  fi
}

sfx_request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local url
  local response_file
  local http_code

  url="$(sfx_api_base_url)${path}"
  response_file="$(mktemp)"
  if [[ -n "${body}" ]]; then
    http_code="$(curl -sS -o "${response_file}" -w '%{http_code}' \
      -X "${method}" \
      -H "X-SF-TOKEN: ${SPLUNK_O11Y_API_TOKEN}" \
      -H 'Content-Type: application/json' \
      "${url}" \
      -d "${body}")"
  else
    http_code="$(curl -sS -o "${response_file}" -w '%{http_code}' \
      -X "${method}" \
      -H "X-SF-TOKEN: ${SPLUNK_O11Y_API_TOKEN}" \
      "${url}")"
  fi

  if [[ ! "${http_code}" =~ ^2 ]]; then
    warn "Splunk Observability ${method} ${path} returned ${http_code}"
    cat "${response_file}" >&2
    rm -f "${response_file}"
    return 1
  fi

  cat "${response_file}"
  rm -f "${response_file}"
}

sfx_delete() {
  local path="$1"
  local url
  url="$(sfx_api_base_url)${path}"
  curl -sS -X DELETE -H "X-SF-TOKEN: ${SPLUNK_O11Y_API_TOKEN}" "${url}" >/dev/null
}

sfx_cleanup_dashboard_package() {
  local state_prefix="$1"
  local dashboard_id
  local chart_id
  local group_id
  local key

  while IFS= read -r key; do
    [[ -z "${key}" ]] && continue
    if dashboard_id="$(state_get_string "${key}" 2>/dev/null)"; then
      sfx_delete "/v2/dashboard/${dashboard_id}" || true
    fi
  done < <(jq -r \
    --arg prefix "${state_prefix}.dashboards." '
    paths(scalars)
    | map(tostring)
    | join(".")
    | select(startswith($prefix))
  ' "${demo_state_file}")

  while IFS= read -r key; do
    [[ -z "${key}" ]] && continue
    if chart_id="$(state_get_string "${key}" 2>/dev/null)"; then
      sfx_delete "/v2/chart/${chart_id}" || true
    fi
  done < <(jq -r \
    --arg prefix "${state_prefix}.charts." '
    paths(scalars)
    | map(tostring)
    | join(".")
    | select(startswith($prefix))
  ' "${demo_state_file}")

  if group_id="$(state_get_string "${state_prefix}.group_id" 2>/dev/null)"; then
    sfx_delete "/v2/dashboardgroup/${group_id}" || true
  fi

  state_delete_key "${state_prefix}" || true
}

sfx_prune_empty_group_dashboards() {
  local group_id="$1"
  local group_name="$2"
  local response=""
  local dashboard_id
  local dashboard_json
  local dashboard_name
  local chart_count

  if ! response="$(sfx_request GET "/v2/dashboardgroup/${group_id}")"; then
    return 0
  fi

  while IFS= read -r dashboard_id; do
    [[ -z "${dashboard_id}" ]] && continue
    dashboard_json="$(sfx_request GET "/v2/dashboard/${dashboard_id}" || true)"
    [[ -n "${dashboard_json}" ]] || continue

    dashboard_name="$(jq -r '.name // ""' <<<"${dashboard_json}")"
    chart_count="$(jq -r '(.charts // []) | length' <<<"${dashboard_json}")"

    if [[ "${dashboard_name}" == "${group_name}" && "${chart_count}" == "0" ]]; then
      log "Deleting empty placeholder dashboard ${dashboard_id} from group ${group_name}"
      sfx_delete "/v2/dashboard/${dashboard_id}" || true
    fi
  done < <(jq -r '.dashboards[]?' <<<"${response}")
}

sfx_upsert_dashboard_group() {
  local state_key="$1"
  local name="$2"
  local description="$3"
  local group_id=""
  local payload
  local response

  payload="$(jq -cn \
    --arg name "${name}" \
    --arg description "${description}" \
    '{name: $name, description: $description}')"

  group_id="$(state_get_string "${state_key}" 2>/dev/null || true)"
  if [[ -n "${group_id}" ]]; then
    printf '%s' "${group_id}"
    return 0
  fi

  response="$(sfx_request POST "/v2/dashboardgroup" "${payload}")"
  group_id="$(jq -r '.id' <<<"${response}")"
  state_set_string "${state_key}" "${group_id}"
  printf '%s' "${group_id:-$(jq -r '.id' <<<"${response}")}"
}

sfx_upsert_chart() {
  local state_key="$1"
  local payload="$2"
  local chart_id=""
  local response=""
  local cleaned_payload

  cleaned_payload="$(jq -c 'del(.. | nulls)' <<<"${payload}")"
  chart_id="$(state_get_string "${state_key}" 2>/dev/null || true)"
  if [[ -n "${chart_id}" ]]; then
    if response="$(sfx_request PUT "/v2/chart/${chart_id}" "${cleaned_payload}")"; then
      printf '%s' "${chart_id}"
      return 0
    fi
    chart_id=""
  fi

  if [[ -z "${chart_id}" ]]; then
    response="$(sfx_request POST "/v2/chart" "${cleaned_payload}")"
    chart_id="$(jq -r '.id' <<<"${response}")"
    state_set_string "${state_key}" "${chart_id}"
  fi

  printf '%s' "${chart_id:-$(jq -r '.id' <<<"${response}")}"
}

sfx_upsert_dashboard() {
  local state_key="$1"
  local payload="$2"
  local dashboard_id=""
  local response=""
  local cleaned_payload

  cleaned_payload="$(jq -c 'del(.. | nulls)' <<<"${payload}")"
  dashboard_id="$(state_get_string "${state_key}" 2>/dev/null || true)"
  if [[ -n "${dashboard_id}" ]]; then
    if response="$(sfx_request PUT "/v2/dashboard/${dashboard_id}" "${cleaned_payload}")"; then
      printf '%s' "${dashboard_id}"
      return 0
    fi
    dashboard_id=""
  fi

  if [[ -z "${dashboard_id}" ]]; then
    response="$(sfx_request POST "/v2/dashboard" "${cleaned_payload}")"
    dashboard_id="$(jq -r '.id' <<<"${response}")"
    state_set_string "${state_key}" "${dashboard_id}"
  fi

  printf '%s' "${dashboard_id:-$(jq -r '.id' <<<"${response}")}"
}

sfx_time_chart_payload() {
  local name="$1"
  local description="$2"
  local program_text="$3"
  local display_name="$4"
  local label="$5"
  local unit="$6"
  local no_data_message="$7"

  jq -cn \
    --arg name "${name}" \
    --arg description "${description}" \
    --arg programText "${program_text}" \
    --arg displayName "${display_name}" \
    --arg label "${label}" \
    --arg unit "${unit}" \
    --arg noDataMessage "${no_data_message}" '
    {
      name: $name,
      description: $description,
      programText: $programText,
      tags: ["filaops", "3dprint", "demo"],
      options: {
        type: "TimeSeriesChart",
        colorBy: "Dimension",
        defaultPlotType: "LineChart",
        includeZero: false,
        stacked: false,
        showEventLines: true,
        unitPrefix: "Metric",
        time: {type: "relative", range: 3600000, rangeEnd: 0},
        axes: [{label: ""}, {label: ""}],
        lineChartOptions: {showDataMarkers: false},
        areaChartOptions: {showDataMarkers: false},
        histogramChartOptions: {colorThemeIndex: 16},
        legendOptions: {fields: null},
        onChartLegendOptions: {showLegend: false},
        noDataOptions: {noDataMessage: $noDataMessage},
        programOptions: {disableSampling: false, maxDelay: 0, minimumResolution: 0},
        publishLabelOptions: [{
          displayName: $displayName,
          label: $label,
          valueUnit: (if $unit == "" then null else $unit end),
          valueSuffix: null,
          valuePrefix: null,
          yAxis: 0
        }]
      }
    }'
}

sfx_single_value_chart_payload() {
  local name="$1"
  local description="$2"
  local program_text="$3"
  local display_name="$4"
  local label="$5"
  local value_suffix="$6"
  local no_data_message="$7"

  jq -cn \
    --arg name "${name}" \
    --arg description "${description}" \
    --arg programText "${program_text}" \
    --arg displayName "${display_name}" \
    --arg label "${label}" \
    --arg valueSuffix "${value_suffix}" \
    --arg noDataMessage "${no_data_message}" '
    {
      name: $name,
      description: $description,
      programText: $programText,
      tags: ["filaops", "3dprint", "demo"],
      options: {
        type: "SingleValue",
        colorBy: "Dimension",
        unitPrefix: "Metric",
        time: {type: "relative", range: 3600000, rangeEnd: 0},
        showSparkLine: false,
        secondaryVisualization: "None",
        timestampHidden: false,
        noDataOptions: {noDataMessage: $noDataMessage},
        programOptions: {disableSampling: false, maxDelay: 0, minimumResolution: 0},
        publishLabelOptions: [{
          displayName: $displayName,
          label: $label,
          valueSuffix: (if $valueSuffix == "" then null else $valueSuffix end),
          valuePrefix: null,
          valueUnit: null,
          yAxis: 0
        }]
      }
    }'
}

sfx_text_chart_payload() {
  local name="$1"
  local markdown="$2"

  jq -cn \
    --arg name "${name}" \
    --arg markdown "${markdown}" '
    {
      name: $name,
      options: {
        type: "Text",
        markdown: $markdown
      },
      tags: ["filaops", "3dprint", "demo"]
    }'
}

sfx_import_dashboard_package() {
  local package_path="$1"
  local state_prefix="$2"
  local package_json
  local group_name
  local group_description
  local group_id
  local chart_map='{}'
  local chart_export
  local old_chart_id
  local chart_payload
  local new_chart_id
  local dashboard_export
  local old_dashboard_id
  local dashboard_payload
  local new_dashboard_id
  local dashboard_name

  package_json="$(cat "${package_path}")"
  group_name="$(jq -r '.groupExport.group.name' <<<"${package_json}")"
  group_description="$(jq -r '.groupExport.group.description // ""' <<<"${package_json}")"
  group_id="$(sfx_upsert_dashboard_group "${state_prefix}.group_id" "${group_name}" "${group_description}")"
  state_set_string "${state_prefix}.group_name" "${group_name}"

  while IFS= read -r chart_export; do
    old_chart_id="$(jq -r '.chart.id' <<<"${chart_export}")"
    chart_payload="$(jq -c '
      .chart
      | del(
          .id,
          .created,
          .creator,
          .lastUpdated,
          .lastUpdatedBy,
          .autoDetectRelatedDetectorIds,
          .relatedDetectorIds,
          .packageSpecifications,
          .customProperties
        )
    ' <<<"${chart_export}")"
    new_chart_id="$(sfx_upsert_chart "${state_prefix}.charts.${old_chart_id}" "${chart_payload}")"
    chart_map="$(jq -cn --argjson map "${chart_map}" --arg old "${old_chart_id}" --arg new "${new_chart_id}" '$map + {($old): $new}')"
  done < <(jq -c '.chartExports[]' <<<"${package_json}")

  while IFS= read -r dashboard_export; do
    old_dashboard_id="$(jq -r '.dashboard.id' <<<"${dashboard_export}")"
    dashboard_name="$(jq -r '.dashboard.name' <<<"${dashboard_export}")"
    dashboard_payload="$(jq -c \
      --arg groupId "${group_id}" \
      --argjson chartMap "${chart_map}" '
      .dashboard
      | {
          name,
          description,
          chartDensity,
          groupId: $groupId,
          charts: (.charts | map(.chartId = ($chartMap[.chartId] // .chartId))),
          filters: (.filters // {variables: []})
        }
      | del(.. | nulls)
    ' <<<"${dashboard_export}")"
    new_dashboard_id="$(sfx_upsert_dashboard "${state_prefix}.dashboards.${old_dashboard_id}" "${dashboard_payload}")"
    state_set_string "${state_prefix}.dashboard_names.$(slugify "${dashboard_name}")" "${new_dashboard_id}"
  done < <(jq -c '.dashboardExports[]' <<<"${package_json}")

  sfx_prune_empty_group_dashboards "${group_id}" "${group_name}"
}

sfx_post_event_marker() {
  local phase="$1"
  local run_id="$2"
  local message="$3"
  local url
  local timestamp_ms
  local payload

  url="$(sfx_ingest_base_url)/v2/event"
  timestamp_ms="$(( $(date +%s) * 1000 ))"
  payload="$(jq -cn \
    --arg phase "${phase}" \
    --arg runId "${run_id}" \
    --arg namespace "${NAMESPACE:-3dprint}" \
    --arg message "${message}" \
    --argjson timestamp "${timestamp_ms}" '
    {
      category: "USER_DEFINED",
      eventType: "FilaOps Demo Marker",
      dimensions: {
        app: "filaops",
        namespace: $namespace,
        phase: $phase,
        run_id: $runId
      },
      properties: {
        message: $message,
        source: "scripts/demo/3dprint-observability.sh"
      },
      timestamp: $timestamp
    }')"

  curl -sS -X POST \
    -H "X-SF-TOKEN: $(sfx_ingest_token)" \
    -H 'Content-Type: application/json' \
    "${url}" \
    -d "${payload}" >/dev/null
}

sfx_demo_note_markdown() {
  local run_id="$1"
  local te_group_url=""
  local network_explorer_url="${SPLUNK_NETWORK_EXPLORER_URL:-}"
  local isovalent_url="${ISOVALENT_DASHBOARD_URL:-}"
  local isovalent_cilium_url=""
  local isovalent_hubble_url=""
  local quota_note=""
  local vendor_package_note=""

  if te_group_url="$(state_get_string "splunk.packages.vendor_te.dashboard_names.application" 2>/dev/null)"; then
    te_group_url="$(sfx_dashboard_url "${te_group_url}")"
  else
    te_group_url="${THOUSANDEYES_DASHBOARD_URL:-}"
  fi

  if [[ "${THOUSANDEYES_PIN_EXISTING_TRANSACTION_TESTS:-false}" == "true" ]]; then
    quota_note="Transaction-test quota is currently pinned, so these custom dashboards use the live FilaOps HTTP test plus backend telemetry for guaranteed data."
  fi

  if [[ -z "${isovalent_url}" ]]; then
    isovalent_cilium_url="$(state_get_string "splunk.isovalent.dashboard_urls.cilium_policy_verdicts" 2>/dev/null || true)"
    isovalent_hubble_url="$(state_get_string "splunk.isovalent.dashboard_urls.hubble_network_overview" 2>/dev/null || true)"
  fi

  if [[ "$(state_get_string "thousandeyes.vendor_dashboards_supported" 2>/dev/null || printf 'true')" != "true" ]]; then
    vendor_package_note="Pinned shared ThousandEyes browser/API tests do not match the FilaOps demo target, so the generic imported ThousandEyes package is skipped to avoid empty or misleading panels."
  fi

  jq -rn \
    --arg runId "${run_id}" \
    --arg teUrl "${te_group_url}" \
    --arg networkExplorerUrl "${network_explorer_url}" \
    --arg isovalentUrl "${isovalent_url}" \
    --arg isovalentCiliumUrl "${isovalent_cilium_url}" \
    --arg isovalentHubbleUrl "${isovalent_hubble_url}" \
    --arg quotaNote "${quota_note}" \
    --arg vendorPackageNote "${vendor_package_note}" '
    [
      "### Demo context",
      "",
      "* Current `RUN_ID`: `" + $runId + "`",
      "* ThousandEyes view: " + (if $teUrl == "" then "set `THOUSANDEYES_DASHBOARD_URL` or run `setup` first" else "[open ThousandEyes-linked dashboard](" + $teUrl + ")" end),
      "* Splunk Network Explorer: " + (if $networkExplorerUrl == "" then "open Splunk Observability Cloud > Network Explorer and filter to namespace `3dprint` or service `filaops-backend`" else "[open Network Explorer](" + $networkExplorerUrl + ")" end),
      "* Isovalent view: " + (
        if $isovalentUrl != "" then
          "[open Isovalent dashboard](" + $isovalentUrl + ")"
        elif $isovalentCiliumUrl != "" or $isovalentHubbleUrl != "" then
          [
            (if $isovalentCiliumUrl == "" then empty else "[open Cilium Policy Verdicts](" + $isovalentCiliumUrl + ")" end),
            (if $isovalentHubbleUrl == "" then empty else "[open Hubble Network Overview](" + $isovalentHubbleUrl + ")" end)
          ] | join(" | ")
        else
          "set `ISOVALENT_DASHBOARD_URL` to add a direct handoff link"
        end
      ),
      "",
      "Baseline story: front door stays healthy while the reversible policy blocks `backend -> order-ingest` during order import."
    ]
    + (if $quotaNote == "" then [] else ["", "_Quota mode_: " + $quotaNote] end)
    + (if $vendorPackageNote == "" then [] else ["", "_Dashboard package note_: " + $vendorPackageNote] end)
    | join("\n")'
}

sfx_te_metric_program() {
  local metric_name="$1"
  local test_id="$2"
  jq -rn \
    --arg metric "${metric_name}" \
    --arg testId "${test_id}" \
    'if $testId == "" then
       "A = data(\($metric|@json)).publish(label=\"A\")"
     else
       "A = data(\($metric|@json), filter=filter(\"thousandeyes.test.id\", \($testId|@json))).publish(label=\"A\")"
     end'
}

sfx_demo_dashboards() {
  local run_id="$1"
  local group_id
  local note_chart_id
  local app_te_dashboard_id
  local policy_dashboard_id
  local http_test_id=""
  local web_test_id=""
  local api_test_id=""
  local isovalent_cilium_url=""
  local isovalent_hubble_url=""
  local note_markdown
  local chart_ids_json='{}'
  local policy_chart_ids_json='{}'
  local payload

  group_id="$(sfx_upsert_dashboard_group \
    "splunk.groups.demo" \
    "FilaOps Cross-Observability Demo" \
    "Manufacturing app views correlated with ThousandEyes front-door telemetry and Isovalent policy context.")"

  if http_test_id="$(state_get_string "thousandeyes.tests.http_server.id" 2>/dev/null)"; then :; else http_test_id=""; fi
  if web_test_id="$(state_get_string "thousandeyes.tests.web_transaction.id" 2>/dev/null)"; then :; else web_test_id=""; fi
  if api_test_id="$(state_get_string "thousandeyes.tests.api.id" 2>/dev/null)"; then :; else api_test_id=""; fi
  if [[ -z "${ISOVALENT_DASHBOARD_URL:-}" ]]; then
    isovalent_cilium_url="$(state_get_string "splunk.isovalent.dashboard_urls.cilium_policy_verdicts" 2>/dev/null || true)"
    isovalent_hubble_url="$(state_get_string "splunk.isovalent.dashboard_urls.hubble_network_overview" 2>/dev/null || true)"
  fi

  note_markdown="$(sfx_demo_note_markdown "${run_id}")"
  note_chart_id="$(sfx_upsert_chart \
    "splunk.demo.charts.note" \
    "$(sfx_text_chart_payload "FilaOps Demo Context" "${note_markdown}")")"

  chart_ids_json="$(jq -cn --arg chartId "${note_chart_id}" '{"note": $chartId}')"

  payload="$(sfx_single_value_chart_payload \
    "Frontend HTTP availability" \
    "ThousandEyes HTTP Server availability for the external frontend URL." \
    "$(sfx_te_metric_program "http.server.request.availability" "${http_test_id}" "HTTP availability")" \
    "HTTP availability" "A" "%" \
    "Run \`setup\` after provisioning the ThousandEyes HTTP test.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.http_availability" "${payload}")" '$map + {"http_availability": $id}')"

  payload="$(sfx_single_value_chart_payload \
    "Frontend network latency" \
    "ThousandEyes network latency for the live FilaOps HTTP synthetic." \
    "$(sfx_te_metric_program "network.latency" "${http_test_id}" "Frontend network latency")" \
    "Frontend network latency" "A" "ms" \
    "No ThousandEyes latency data yet for the FilaOps HTTP test.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.browser_completion" "${payload}")" '$map + {"browser_completion": $id}')"

  payload="$(sfx_single_value_chart_payload \
    "Frontend network loss" \
    "ThousandEyes packet loss for the live FilaOps HTTP synthetic." \
    "$(sfx_te_metric_program "network.loss" "${http_test_id}" "Frontend network loss")" \
    "Frontend network loss" "A" "%" \
    "No ThousandEyes loss data yet for the FilaOps HTTP test.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.api_completion" "${payload}")" '$map + {"api_completion": $id}')"

  payload="$(sfx_time_chart_payload \
    "Frontend HTTP duration" \
    "ThousandEyes HTTP client duration for the live FilaOps frontend synthetic." \
    "$(sfx_te_metric_program "http.client.request.duration" "${http_test_id}" "Frontend HTTP duration")" \
    "Frontend HTTP duration" "A" "Millisecond" \
    "No ThousandEyes HTTP duration data yet.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.browser_duration" "${payload}")" '$map + {"browser_duration": $id}')"

  payload="$(sfx_time_chart_payload \
    "Backend order import latency" \
    "Backend OTel HTTP latency for the order import endpoint. If your org uses different HTTP semconv metric names, adjust the program text in the chart." \
    "A = data('http.server.request.duration', filter=filter('service.name', 'filaops-backend') and filter('http.route', '/api/v1/admin/orders/import')).mean().publish(label='A')" \
    "Backend order import latency" "A" "Second" \
    'No matching OTel metric found. Confirm the backend is sending `http.server.request.duration`.')"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.backend_import_latency" "${payload}")" '$map + {"backend_import_latency": $id}')"

  payload="$(sfx_time_chart_payload \
    "Order import request volume" \
    "Count of order import requests observed by the backend." \
    "A = data('http.server.request.duration', filter=filter('service.name', 'filaops-backend') and filter('http.route', '/api/v1/admin/orders/import')).count().publish(label='A')" \
    "Order import requests" "A" "" \
    'No matching OTel metric found. Confirm the backend is sending `http.server.request.duration` for the order-import route.')"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.backend_import_502s" "${payload}")" '$map + {"backend_import_502s": $id}')"

  payload="$(sfx_time_chart_payload \
    "Frontend network jitter" \
    "ThousandEyes network jitter for the live FilaOps HTTP synthetic." \
    "$(sfx_te_metric_program "network.jitter" "${http_test_id}" "Frontend network jitter")" \
    "Frontend network jitter" "A" "Millisecond" \
    "No ThousandEyes jitter data yet.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.api_step_completion" "${payload}")" '$map + {"api_step_completion": $id}')"

  payload="$(sfx_time_chart_payload \
    "App trace health" \
    "Backend request rate from Splunk APM. Correlate with ThousandEyes synthetic signals above." \
    "A = data('service.request.count', filter=filter('sf_service', 'filaops-backend') and filter('sf_environment', '3dprint')).sum().publish(label='A')" \
    "Requests/sec" "A" "" \
    "No APM request data yet. Confirm the backend is sending traces to Splunk.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.trace_health" "${payload}")" '$map + {"trace_health": $id}')"

  payload="$(sfx_time_chart_payload \
    "TE synthetic vs app latency" \
    "Overlay: ThousandEyes HTTP client duration and backend order-import OTel latency." \
    "$(printf '%s\n%s' \
      "$(sfx_te_metric_program "http.client.request.duration" "${http_test_id}" "TE synthetic latency")" \
      "B = data('http.server.request.duration', filter=filter('service.name', 'filaops-backend') and filter('http.route', '/api/v1/admin/orders/import')).mean().publish(label='B')")" \
    "TE synthetic latency" "A" "Millisecond" \
    "Waiting for both ThousandEyes and backend metrics.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.te_vs_app_latency" "${payload}")" '$map + {"te_vs_app_latency": $id}')"

  payload="$(sfx_text_chart_payload \
    "APM service map" \
    "### Splunk APM\n\nOpen [APM Service Map](https://app.${SPLUNK_O11Y_REALM}.signalfx.com/#/apm?environments=3dprint) filtered to the \`3dprint\` environment to see the full service dependency graph and trace correlation with ThousandEyes synthetics.")"
  chart_ids_json="$(jq -cn --argjson map "${chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.apm_link" "${payload}")" '$map + {"apm_link": $id}')"

  payload="$(jq -cn \
    --arg name "FilaOps Demo - App + ThousandEyes" \
    --arg description "Live ThousandEyes HTTP and network telemetry beside the app's backend order-import metrics and trace correlation." \
    --arg groupId "${group_id}" \
    --argjson charts "${chart_ids_json}" '
    {
      name: $name,
      description: $description,
      groupId: $groupId,
      chartDensity: "DEFAULT",
      filters: {variables: []},
      charts: [
        {chartId: $charts.note, column: 0, row: 0, width: 12, height: 1},
        {chartId: $charts.http_availability, column: 0, row: 1, width: 4, height: 1},
        {chartId: $charts.browser_completion, column: 4, row: 1, width: 4, height: 1},
        {chartId: $charts.api_completion, column: 8, row: 1, width: 4, height: 1},
        {chartId: $charts.browser_duration, column: 0, row: 2, width: 12, height: 1},
        {chartId: $charts.backend_import_latency, column: 0, row: 3, width: 6, height: 1},
        {chartId: $charts.api_step_completion, column: 6, row: 3, width: 6, height: 1},
        {chartId: $charts.backend_import_502s, column: 0, row: 4, width: 12, height: 1},
        {chartId: $charts.apm_link, column: 0, row: 5, width: 12, height: 1},
        {chartId: $charts.trace_health, column: 0, row: 6, width: 6, height: 1},
        {chartId: $charts.te_vs_app_latency, column: 6, row: 6, width: 6, height: 1}
      ]
    }')"
  app_te_dashboard_id="$(sfx_upsert_dashboard "splunk.demo.dashboards.app_and_te" "${payload}")"
  state_set_string "splunk.demo.dashboard_names.app_and_te" "${app_te_dashboard_id}"

  policy_chart_ids_json="$(jq -cn --arg id "$(sfx_upsert_chart \
    "splunk.demo.charts.policy_note" \
    "$(sfx_text_chart_payload "FilaOps Demo Context" "${note_markdown}")")" '{"note": $id}')"

  payload="$(sfx_single_value_chart_payload \
    "Frontend network latency" \
    "ThousandEyes network latency for the live FilaOps HTTP synthetic." \
    "$(sfx_te_metric_program "network.latency" "${http_test_id}" "Frontend network latency")" \
    "Frontend network latency" "A" "ms" \
    "No ThousandEyes latency data yet for the FilaOps HTTP test.")"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.policy_browser_completion" "${payload}")" '$map + {"browser_completion": $id}')"

  payload="$(sfx_single_value_chart_payload \
    "Frontend HTTP availability" \
    "ThousandEyes HTTP Server availability for the external frontend URL." \
    "$(sfx_te_metric_program "http.server.request.availability" "${http_test_id}" "Frontend HTTP availability")" \
    "Frontend HTTP availability" "A" "%" \
    "No ThousandEyes HTTP availability data yet.")"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.policy_api_completion" "${payload}")" '$map + {"api_completion": $id}')"

  payload="$(sfx_time_chart_payload \
    "Backend order import latency" \
    "Backend OTel HTTP latency for the order import endpoint. If your org uses different HTTP semconv metric names, adjust the program text in the chart." \
    "A = data('http.server.request.duration', filter=filter('service.name', 'filaops-backend') and filter('http.route', '/api/v1/admin/orders/import')).mean().publish(label='A')" \
    "Backend order import latency" "A" "Second" \
    'No matching OTel metric found. Confirm the backend is sending `http.server.request.duration`.')"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.policy_backend_import_latency" "${payload}")" '$map + {"backend_import_latency": $id}')"

  payload="$(sfx_time_chart_payload \
    "Order import request volume" \
    "Count of order import requests observed by the backend." \
    "A = data('http.server.request.duration', filter=filter('service.name', 'filaops-backend') and filter('http.route', '/api/v1/admin/orders/import')).count().publish(label='A')" \
    "Order import requests" "A" "" \
    'No matching OTel metric found. Confirm the backend is sending `http.server.request.duration` for the order-import route.')"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.policy_backend_import_502s" "${payload}")" '$map + {"backend_import_502s": $id}')"

  payload="$(sfx_text_chart_payload \
    "Isovalent handoff" \
    "$(jq -rn \
      --arg url "${ISOVALENT_DASHBOARD_URL:-}" \
      --arg ciliumUrl "${isovalent_cilium_url}" \
      --arg hubbleUrl "${isovalent_hubble_url}" '
      if $url != "" then
        "### Isovalent correlation\n\n[Open the Isovalent dashboard](" + $url + ")\n\nUse it beside the Splunk event markers to show the policy application and recovery."
      elif $ciliumUrl != "" or $hubbleUrl != "" then
        "### Isovalent correlation\n\n"
        + ([
            (if $ciliumUrl == "" then empty else "* [Open Cilium Policy Verdicts](" + $ciliumUrl + ")" end),
            (if $hubbleUrl == "" then empty else "* [Open Hubble Network Overview](" + $hubbleUrl + ")" end)
          ] | join("\n"))
        + "\n\nUse these built-in dashboards beside the Splunk event markers to show the policy application and recovery."
      else
        "### Isovalent correlation\n\nSet `ISOVALENT_DASHBOARD_URL` to attach the live Isovalent dashboard.\n\nIf Cilium or Hubble metrics are already ingested into Splunk Observability, the adjacent charts will populate automatically."
      end')")"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.isovalent_note" "${payload}")" '$map + {"isovalent_note": $id}')"

  local cilium_drop_metric="${ISOVALENT_DROP_METRIC:-cilium_drop_count_total}"
  local hubble_flow_metric="${ISOVALENT_FLOW_METRIC:-hubble_flows_processed_total}"
  local ns_dim="${ISOVALENT_NAMESPACE_DIMENSION:-k8s_namespace_name}"

  payload="$(sfx_time_chart_payload \
    "Cilium packet drops" \
    "Cilium drop counter by reason and direction. Falls back to ThousandEyes HTTP duration if Hubble metrics are not ingested." \
    "A = data('${cilium_drop_metric}', filter=filter('${ns_dim}', '${NAMESPACE:-3dprint}')).sum(by=['reason', 'direction']).publish(label='A')" \
    "Cilium drops" "A" "" \
    "No Cilium drop metrics found. Enable Hubble metrics and configure the collector to scrape them, or use the Isovalent dashboard handoff.")"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.cilium_drops" "${payload}")" '$map + {"cilium_drops": $id}')"

  payload="$(sfx_time_chart_payload \
    "Hubble flow volume" \
    "Hubble processed flows by type and verdict. Falls back to ThousandEyes network loss if Hubble metrics are not ingested." \
    "A = data('${hubble_flow_metric}', filter=filter('${ns_dim}', '${NAMESPACE:-3dprint}')).sum(by=['type', 'verdict']).publish(label='A')" \
    "Hubble flows" "A" "" \
    "No Hubble flow metrics found. Enable Hubble metrics and configure the collector to scrape them, or use the Isovalent dashboard handoff.")"
  policy_chart_ids_json="$(jq -cn --argjson map "${policy_chart_ids_json}" --arg id "$(sfx_upsert_chart "splunk.demo.charts.hubble_flows" "${payload}")" '$map + {"hubble_flows": $id}')"

  payload="$(jq -cn \
    --arg name "FilaOps Demo - Policy Impact" \
    --arg description "Order-import failure correlated with ThousandEyes, event markers, and Isovalent policy context." \
    --arg groupId "${group_id}" \
    --argjson charts "${policy_chart_ids_json}" '
    {
      name: $name,
      description: $description,
      groupId: $groupId,
      chartDensity: "DEFAULT",
      filters: {variables: []},
      charts: [
        {chartId: $charts.note, column: 0, row: 0, width: 12, height: 1},
        {chartId: $charts.backend_import_502s, column: 0, row: 1, width: 6, height: 1},
        {chartId: $charts.api_completion, column: 6, row: 1, width: 3, height: 1},
        {chartId: $charts.browser_completion, column: 9, row: 1, width: 3, height: 1},
        {chartId: $charts.backend_import_latency, column: 0, row: 2, width: 12, height: 1},
        {chartId: $charts.isovalent_note, column: 0, row: 3, width: 12, height: 1},
        {chartId: $charts.cilium_drops, column: 0, row: 4, width: 6, height: 1},
        {chartId: $charts.hubble_flows, column: 6, row: 4, width: 6, height: 1}
      ]
    }')"
  policy_dashboard_id="$(sfx_upsert_dashboard "splunk.demo.dashboards.policy_impact" "${payload}")"
  state_set_string "splunk.demo.dashboard_names.policy_impact" "${policy_dashboard_id}"

  sfx_prune_empty_group_dashboards "${group_id}" "FilaOps Cross-Observability Demo"
}

sfx_print_links() {
  local dashboard_id
  local name

  printf 'Splunk Observability Cloud\n'
  for name in app_and_te policy_impact; do
    dashboard_id="$(state_get_string "splunk.demo.dashboard_names.${name}" 2>/dev/null || true)"
    if [[ -n "${dashboard_id}" ]]; then
      printf '  %-18s %s\n' "${name}" "$(sfx_dashboard_url "${dashboard_id}")"
    fi
  done

  dashboard_id="$(state_get_string "splunk.packages.vendor_te.dashboard_names.application" 2>/dev/null || true)"
  if [[ -n "${dashboard_id}" ]]; then
    printf '  %-18s %s\n' "te-application" "$(sfx_dashboard_url "${dashboard_id}")"
  fi
  dashboard_id="$(state_get_string "splunk.packages.vendor_te.dashboard_names.network" 2>/dev/null || true)"
  if [[ -n "${dashboard_id}" ]]; then
    printf '  %-18s %s\n' "te-network" "$(sfx_dashboard_url "${dashboard_id}")"
  fi

  if [[ -n "${THOUSANDEYES_DASHBOARD_URL:-}" ]]; then
    printf 'ThousandEyes\n  %-18s %s\n' "dashboard" "${THOUSANDEYES_DASHBOARD_URL}"
  fi
  if [[ -n "${SPLUNK_NETWORK_EXPLORER_URL:-}" ]]; then
    printf 'Splunk Observability Cloud\n  %-18s %s\n' "network-explorer" "${SPLUNK_NETWORK_EXPLORER_URL}"
  fi
  if [[ -n "${ISOVALENT_DASHBOARD_URL:-}" ]]; then
    printf 'Isovalent\n  %-18s %s\n' "dashboard" "${ISOVALENT_DASHBOARD_URL}"
  else
    dashboard_id="$(state_get_string "splunk.isovalent.dashboard_urls.cilium_policy_verdicts" 2>/dev/null || true)"
    if [[ -n "${dashboard_id}" ]]; then
      printf 'Isovalent\n  %-18s %s\n' "cilium-policy" "${dashboard_id}"
    fi
    dashboard_id="$(state_get_string "splunk.isovalent.dashboard_urls.hubble_network_overview" 2>/dev/null || true)"
    if [[ -n "${dashboard_id}" ]]; then
      printf 'Isovalent\n  %-18s %s\n' "hubble-network" "${dashboard_id}"
    fi
  fi
}

sfx_cleanup_remote_assets() {
  local dashboard_id
  local chart_id
  local group_id
  local key

  for key in \
    "splunk.demo.dashboards.policy_impact" \
    "splunk.demo.dashboards.app_and_te" \
    "splunk.packages.vendor_te.dashboard_names.application" \
    "splunk.packages.vendor_te.dashboard_names.network" \
    "splunk.packages.vendor_te.dashboard_names.configuration"
  do
    if dashboard_id="$(state_get_string "${key}" 2>/dev/null)"; then
      sfx_delete "/v2/dashboard/${dashboard_id}" || true
    fi
  done

  while IFS= read -r key; do
    if chart_id="$(state_get_string "${key}" 2>/dev/null)"; then
      sfx_delete "/v2/chart/${chart_id}" || true
    fi
  done < <(jq -r '
    paths(scalars)
    | map(tostring)
    | join(".")
    | select(startswith("splunk.demo.charts.") or startswith("splunk.packages.vendor_te.charts."))
  ' "${demo_state_file}")

  for key in "splunk.groups.demo" "splunk.packages.vendor_te.group_id"; do
    if group_id="$(state_get_string "${key}" 2>/dev/null)"; then
      sfx_delete "/v2/dashboardgroup/${group_id}" || true
    fi
  done
}
