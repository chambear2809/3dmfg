#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
demo_root="${repo_root}/scripts/demo"
demo_assets_root="${demo_root}/assets"
demo_state_dir="${DEMO_STATE_DIR:-${demo_root}/.state}"
demo_state_file="${DEMO_STATE_FILE:-${demo_state_dir}/state.json}"

mkdir -p "${demo_state_dir}"
if [[ ! -f "${demo_state_file}" ]]; then
  printf '{}\n' > "${demo_state_file}"
fi

log() {
  printf '[demo] %s\n' "$*" >&2
}

warn() {
  printf '[demo][warn] %s\n' "$*" >&2
}

die() {
  printf '[demo][error] %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || die "Missing required command: ${cmd}"
}

ensure_prereqs() {
  local cmd
  for cmd in curl jq; do
    require_cmd "${cmd}"
  done
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "${value}"
}

require_env() {
  local name
  for name in "$@"; do
    [[ -n "${!name:-}" ]] || die "Missing required environment variable: ${name}"
  done
}

json_path_for_key() {
  local key="$1"
  jq -cn --arg key "${key}" '$key | split(".")'
}

state_get_json() {
  local key="$1"
  local path
  path="$(json_path_for_key "${key}")"
  jq -c --argjson path "${path}" 'getpath($path) // empty' "${demo_state_file}"
}

state_get_string() {
  local key="$1"
  local value
  value="$(state_get_json "${key}")"
  if [[ -z "${value}" || "${value}" == "null" ]]; then
    return 1
  fi
  jq -r '.' <<<"${value}"
}

state_set_json() {
  local key="$1"
  local raw_json="$2"
  local path
  local tmp

  path="$(json_path_for_key "${key}")"
  tmp="$(mktemp)"
  jq --argjson path "${path}" --argjson value "${raw_json}" \
    'setpath($path; $value)' "${demo_state_file}" > "${tmp}"
  mv "${tmp}" "${demo_state_file}"
}

state_set_string() {
  local key="$1"
  local value="$2"
  local path
  local tmp

  path="$(json_path_for_key "${key}")"
  tmp="$(mktemp)"
  jq --argjson path "${path}" --arg value "${value}" \
    'setpath($path; $value)' "${demo_state_file}" > "${tmp}"
  mv "${tmp}" "${demo_state_file}"
}

state_delete_key() {
  local key="$1"
  local path
  local tmp

  path="$(json_path_for_key "${key}")"
  tmp="$(mktemp)"
  jq --argjson path "${path}" 'delpaths([$path])' "${demo_state_file}" > "${tmp}"
  mv "${tmp}" "${demo_state_file}"
}

json_array_from_csv() {
  local csv="$1"
  local -a items=()
  IFS=',' read -r -a items <<<"${csv}"
  printf '%s\n' "${items[@]}" | jq -Rsc 'split("\n") | map(gsub("^\\s+|\\s+$"; "")) | map(select(length > 0))'
}

json_unique_strings() {
  local raw_json="${1:-[]}"
  jq -cn --argjson items "${raw_json}" '$items | map(select(. != null and . != "")) | unique'
}

json_append_string_if_missing() {
  local raw_json="${1:-[]}"
  local value="${2:-}"
  if [[ -z "${value}" ]]; then
    printf '%s' "${raw_json}"
    return 0
  fi
  jq -cn --argjson items "${raw_json}" --arg value "${value}" '$items + [$value] | unique'
}

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-'
}

new_run_id() {
  date '+demo-%Y%m%d%H%M%S'
}

resolve_run_id() {
  local mode="${1:-reuse}"
  local run_id="${RUN_ID:-}"

  if [[ -n "${run_id}" ]]; then
    state_set_string "current_run_id" "${run_id}"
    printf '%s' "${run_id}"
    return 0
  fi

  if [[ "${mode}" == "new" ]]; then
    run_id="$(new_run_id)"
    state_set_string "current_run_id" "${run_id}"
    printf '%s' "${run_id}"
    return 0
  fi

  if run_id="$(state_get_string "current_run_id" 2>/dev/null)"; then
    printf '%s' "${run_id}"
    return 0
  fi

  run_id="$(new_run_id)"
  state_set_string "current_run_id" "${run_id}"
  printf '%s' "${run_id}"
}

read_asset() {
  local relative_path="$1"
  cat "${demo_assets_root}/${relative_path}"
}

replace_template_tokens() {
  local template_path="$1"
  shift
  local content
  local pair
  local key
  local value

  content="$(cat "${template_path}")"
  for pair in "$@"; do
    key="${pair%%=*}"
    value="${pair#*=}"
    content="${content//${key}/${value}}"
  done
  printf '%s' "${content}"
}

safe_api_base_url() {
  local base="${PUBLIC_API_BASE_URL:-${FRONTEND_URL%/}/api/v1}"
  printf '%s' "${base%/}"
}

safe_frontend_url() {
  printf '%s' "${FRONTEND_URL%/}"
}
