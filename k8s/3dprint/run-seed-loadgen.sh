#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NAMESPACE="${NAMESPACE:-3dprint}"
JOB_BASENAME="${JOB_BASENAME:-seed-loadgen-manifest}"
JOB_NAME="${JOB_NAME:-${JOB_BASENAME}-$(date +%Y%m%d%H%M%S)}"
MANIFEST_CONFIGMAP="${MANIFEST_CONFIGMAP:-loadgen-manifest}"
PROFILE="${PROFILE:-small}"
TAG="${TAG:-LG}"
TIMEOUT="${TIMEOUT:-15m}"
JOB_TTL_SECONDS="${JOB_TTL_SECONDS:-600}"
MANIFEST_OUTPUT_PATH="${MANIFEST_OUTPUT_PATH:-}"
ALLOW_PRODUCTION="${ALLOW_PRODUCTION:-false}"
BACKEND_IMAGE="${BACKEND_IMAGE:-}"
ARTIFACT_PATH="/artifacts/manifest.json"

resolve_backend_image() {
  kubectl -n "${NAMESPACE}" get deploy backend \
    -o jsonpath='{.spec.template.spec.containers[?(@.name=="backend")].image}'
}

BACKEND_IMAGE="${BACKEND_IMAGE:-$(resolve_backend_image)}"

if [[ -z "${BACKEND_IMAGE}" ]]; then
  echo "Unable to resolve the backend image from deployment/backend." >&2
  exit 1
fi

kubectl -n "${NAMESPACE}" get configmap filaops-config >/dev/null
kubectl -n "${NAMESPACE}" get secret filaops-secrets >/dev/null

bash "${script_dir}/cleanup-finished-jobs.sh" "${JOB_BASENAME}-" >/dev/null

kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: ${JOB_TTL_SECONDS}
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: seed
          image: ${BACKEND_IMAGE}
          imagePullPolicy: Always
          command:
            - bash
            - -lc
          args:
            - |
              set -euo pipefail
              cmd=(
                python scripts/seed_loadgen_data.py
                --profile "${PROFILE}"
                --manifest "${ARTIFACT_PATH}"
                --tag "${TAG}"
                --admin-email "\${DEMO_ADMIN_EMAIL}"
                --admin-password "\${DEMO_ADMIN_PASSWORD}"
              )
              if [[ "${ALLOW_PRODUCTION}" == "true" ]]; then
                cmd+=(--allow-production)
              fi
              "\${cmd[@]}"
              printf '__LOADGEN_MANIFEST_START__\n'
              cat "${ARTIFACT_PATH}"
              printf '\n__LOADGEN_MANIFEST_END__\n'
          envFrom:
            - configMapRef:
                name: filaops-config
            - secretRef:
                name: filaops-secrets
          volumeMounts:
            - name: artifacts
              mountPath: /artifacts
      volumes:
        - name: artifacts
          emptyDir: {}
EOF

tmp_logs="$(mktemp)"
tmp_manifest="$(mktemp)"
cleanup_tmp() {
  rm -f "${tmp_logs}" "${tmp_manifest}"
}
trap cleanup_tmp EXIT

if kubectl -n "${NAMESPACE}" wait --for=condition=Complete "job/${JOB_NAME}" --timeout="${TIMEOUT}"; then
  kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}" > "${tmp_logs}"
  awk '
    /__LOADGEN_MANIFEST_START__/ {capture=1; next}
    /__LOADGEN_MANIFEST_END__/ {capture=0}
    capture {print}
  ' "${tmp_logs}" > "${tmp_manifest}"

  if [[ ! -s "${tmp_manifest}" ]]; then
    cat "${tmp_logs}"
    echo "Failed to extract manifest JSON from job/${JOB_NAME} logs." >&2
    exit 1
  fi

  kubectl -n "${NAMESPACE}" create configmap "${MANIFEST_CONFIGMAP}" \
    --from-file=manifest.json="${tmp_manifest}" \
    --dry-run=client -o yaml | kubectl apply -f -

  if [[ -n "${MANIFEST_OUTPUT_PATH}" ]]; then
    cp "${tmp_manifest}" "${MANIFEST_OUTPUT_PATH}"
  fi

  cat "${tmp_logs}"
  echo "Updated ConfigMap ${MANIFEST_CONFIGMAP} from job/${JOB_NAME}"
  if [[ -n "${MANIFEST_OUTPUT_PATH}" ]]; then
    echo "Wrote manifest copy to ${MANIFEST_OUTPUT_PATH}"
  fi
  exit 0
fi

kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}" || true
kubectl -n "${NAMESPACE}" describe "job/${JOB_NAME}"
exit 1
