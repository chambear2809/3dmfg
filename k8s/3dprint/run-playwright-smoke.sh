#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-3dprint}"
JOB_BASENAME="${JOB_BASENAME:-playwright-load-smoke}"
JOB_NAME="${JOB_NAME:-${JOB_BASENAME}-$(date +%Y%m%d%H%M%S)}"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-637423309390.dkr.ecr.us-east-1.amazonaws.com/filaops-playwright:load-smoke-amd64-20260401-d9b6388}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://frontend}"
MANIFEST_CONFIGMAP="${MANIFEST_CONFIGMAP:-loadgen-manifest}"
RUN_ID="${RUN_ID:-${JOB_NAME}}"
TIMEOUT="${TIMEOUT:-15m}"
JOB_TTL_SECONDS="${JOB_TTL_SECONDS:-600}"

delete_finished_prefixed_workloads() {
  local prefix="$1"
  local line
  local name
  local active
  local succeeded
  local failed
  local phase

  while IFS='|' read -r name active succeeded failed; do
    [[ -z "${name}" || "${name}" != "${prefix}"* ]] && continue
    active="${active:-0}"
    succeeded="${succeeded:-0}"
    failed="${failed:-0}"

    if [[ "${active}" == "0" && ( "${succeeded}" != "0" || "${failed}" != "0" ) ]]; then
      kubectl -n "${NAMESPACE}" delete job "${name}" --ignore-not-found >/dev/null
    fi
  done < <(
    kubectl -n "${NAMESPACE}" get jobs \
      -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.active}{"|"}{.status.succeeded}{"|"}{.status.failed}{"\n"}{end}'
  )

  while IFS='|' read -r name phase; do
    [[ -z "${name}" || "${name}" != "${prefix}"* ]] && continue
    if [[ "${phase}" == "Succeeded" || "${phase}" == "Failed" ]]; then
      kubectl -n "${NAMESPACE}" delete pod "${name}" --ignore-not-found >/dev/null
    fi
  done < <(
    kubectl -n "${NAMESPACE}" get pods \
      -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.phase}{"\n"}{end}'
  )
}

kubectl -n "${NAMESPACE}" get configmap "${MANIFEST_CONFIGMAP}" >/dev/null
kubectl -n "${NAMESPACE}" get secret filaops-secrets >/dev/null
delete_finished_prefixed_workloads "${JOB_BASENAME}-"

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
        - name: playwright
          image: ${PLAYWRIGHT_IMAGE}
          imagePullPolicy: Always
          command:
            - npx
            - playwright
            - test
            - --project=load-smoke
            - --grep
            - '@load-smoke'
          env:
            - name: CI
              value: "true"
            - name: BASE_URL
              value: ${FRONTEND_BASE_URL}
            - name: RUN_ID
              value: ${RUN_ID}
            - name: LOADGEN_MANIFEST_PATH
              value: /config/manifest.json
            - name: LOADGEN_ADMIN_EMAIL
              valueFrom:
                secretKeyRef:
                  name: filaops-secrets
                  key: DEMO_ADMIN_EMAIL
            - name: LOADGEN_ADMIN_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: filaops-secrets
                  key: DEMO_ADMIN_PASSWORD
          volumeMounts:
            - name: loadgen-manifest
              mountPath: /config
              readOnly: true
      volumes:
        - name: loadgen-manifest
          configMap:
            name: ${MANIFEST_CONFIGMAP}
EOF

if kubectl -n "${NAMESPACE}" wait --for=condition=Complete "job/${JOB_NAME}" --timeout="${TIMEOUT}"; then
  kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}"
  exit 0
fi

kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}" || true
kubectl -n "${NAMESPACE}" describe "job/${JOB_NAME}"
exit 1
