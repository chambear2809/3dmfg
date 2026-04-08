#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-3dprint}"
PREFIXES=("$@")

if [[ ${#PREFIXES[@]} -eq 0 ]]; then
  PREFIXES=(
    "playwright-load-smoke-"
    "seed-loadgen-manifest-"
    "k6-loadgen-"
  )
fi

matches_prefix() {
  local value="$1"
  local prefix
  for prefix in "${PREFIXES[@]}"; do
    if [[ "${value}" == "${prefix}"* ]]; then
      return 0
    fi
  done
  return 1
}

while IFS='|' read -r name active succeeded failed; do
  [[ -z "${name}" ]] && continue
  matches_prefix "${name}" || continue

  active="${active:-0}"
  succeeded="${succeeded:-0}"
  failed="${failed:-0}"

  if [[ "${active}" == "0" && ( "${succeeded}" != "0" || "${failed}" != "0" ) ]]; then
    echo "Deleting finished job ${name}"
    kubectl -n "${NAMESPACE}" delete job "${name}" --ignore-not-found
  fi
done < <(
  kubectl -n "${NAMESPACE}" get jobs \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.active}{"|"}{.status.succeeded}{"|"}{.status.failed}{"\n"}{end}'
)

while IFS='|' read -r name phase; do
  [[ -z "${name}" ]] && continue
  matches_prefix "${name}" || continue

  if [[ "${phase}" == "Succeeded" || "${phase}" == "Failed" ]]; then
    echo "Deleting finished pod ${name}"
    kubectl -n "${NAMESPACE}" delete pod "${name}" --ignore-not-found
  fi
done < <(
  kubectl -n "${NAMESPACE}" get pods \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.phase}{"\n"}{end}'
)
