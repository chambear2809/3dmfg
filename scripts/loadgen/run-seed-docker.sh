#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

args=("$@")
has_manifest=0

for ((i = 0; i < ${#args[@]}; i += 1)); do
  if [[ "${args[$i]}" == "--manifest" ]]; then
    has_manifest=1
    break
  fi
done

if [[ ${has_manifest} -eq 0 ]]; then
  args+=(--manifest /work/scripts/loadgen/manifest.json)
fi

exec docker compose run --rm -T \
  -v "${repo_root}:/work" \
  -w /work/backend \
  backend \
  python scripts/seed_loadgen_data.py "${args[@]}"
