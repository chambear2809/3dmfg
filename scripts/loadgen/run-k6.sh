#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
default_script="scripts/loadgen/main.js"
docker_image="${K6_DOCKER_IMAGE:-grafana/k6:latest}"

if [[ $# -eq 0 ]]; then
  set -- "${default_script}"
fi

run_local() {
  exec k6 run "$@"
}

run_docker() {
  local -a env_args=()
  local env_name
  local docker_base_url="${BASE_URL:-http://host.docker.internal:5173}"
  local docker_api_base_url="${API_BASE_URL:-http://host.docker.internal:8000/api/v1}"
  local passthrough_envs=(
    BASE_URL
    API_BASE_URL
    LOADGEN_ADMIN_EMAIL
    LOADGEN_ADMIN_PASSWORD
    ADMIN_EMAIL
    ADMIN_PASSWORD
    MANIFEST_PATH
    WORKLOAD
    RUN_ID
    COOKIE_POOL_SIZE
    SERVICE_MAP_DURATION
    SERVICE_MAP_VUS
    SERVICE_MAP_SLEEP_MIN_SECONDS
    SERVICE_MAP_SLEEP_MAX_SECONDS
    ASSET_SERVICE_BASE_URL
    ORDER_INGEST_BASE_URL
    PRICING_SERVICE_BASE_URL
    NOTIFICATION_SERVICE_BASE_URL
    K6_WEB_DASHBOARD
    K6_WEB_DASHBOARD_EXPORT
    K6_OUT
  )

  env_args+=(-e "BASE_URL=${docker_base_url}")
  env_args+=(-e "API_BASE_URL=${docker_api_base_url}")

  for env_name in "${passthrough_envs[@]}"; do
    if [[ "${env_name}" == "BASE_URL" || "${env_name}" == "API_BASE_URL" ]]; then
      continue
    fi
    if [[ -n "${!env_name:-}" ]]; then
      env_args+=(-e "${env_name}")
    fi
  done

  exec docker run --rm -i \
    --add-host=host.docker.internal:host-gateway \
    -v "${repo_root}:/work" \
    -w /work \
    "${env_args[@]}" \
    "${docker_image}" \
    run "$@"
}

if command -v k6 >/dev/null 2>&1; then
  run_local "$@"
fi

if command -v docker >/dev/null 2>&1; then
  echo "Local k6 not found; running via Docker image ${docker_image}" >&2
  run_docker "$@"
fi

echo "Neither k6 nor docker is available. Install k6 or run with Docker." >&2
exit 1
