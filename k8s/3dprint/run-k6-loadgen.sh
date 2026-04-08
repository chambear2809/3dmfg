#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

NAMESPACE="${NAMESPACE:-3dprint}"
JOB_BASENAME="${JOB_BASENAME:-k6-loadgen}"
JOB_NAME="${JOB_NAME:-${JOB_BASENAME}-$(date +%Y%m%d%H%M%S)}"
MANIFEST_CONFIGMAP="${MANIFEST_CONFIGMAP:-loadgen-manifest}"
SCRIPT_CONFIGMAP="${SCRIPT_CONFIGMAP:-loadgen-k6-script}"
K6_IMAGE="${K6_IMAGE:-grafana/k6:latest}"
BASE_URL="${BASE_URL:-http://frontend}"
API_BASE_URL="${API_BASE_URL:-${BASE_URL%/}/api/v1}"
WORKLOAD="${WORKLOAD:-service-map}"
RUN_ID="${RUN_ID:-${JOB_NAME}}"
COOKIE_POOL_SIZE="${COOKIE_POOL_SIZE:-3}"
SERVICE_MAP_DURATION="${SERVICE_MAP_DURATION:-4m}"
SERVICE_MAP_VUS="${SERVICE_MAP_VUS:-2}"
SERVICE_MAP_SLEEP_MIN_SECONDS="${SERVICE_MAP_SLEEP_MIN_SECONDS:-1}"
SERVICE_MAP_SLEEP_MAX_SECONDS="${SERVICE_MAP_SLEEP_MAX_SECONDS:-2}"
ASSET_SERVICE_BASE_URL="${ASSET_SERVICE_BASE_URL:-http://asset-service}"
ORDER_INGEST_BASE_URL="${ORDER_INGEST_BASE_URL:-http://order-ingest}"
PRICING_SERVICE_BASE_URL="${PRICING_SERVICE_BASE_URL:-http://pricing-service}"
NOTIFICATION_SERVICE_BASE_URL="${NOTIFICATION_SERVICE_BASE_URL:-http://notification-service}"
TIMEOUT="${TIMEOUT:-30m}"
JOB_TTL_SECONDS="${JOB_TTL_SECONDS:-600}"

kubectl -n "${NAMESPACE}" get configmap "${MANIFEST_CONFIGMAP}" >/dev/null
kubectl -n "${NAMESPACE}" get secret filaops-secrets >/dev/null

kubectl -n "${NAMESPACE}" create configmap "${SCRIPT_CONFIGMAP}" \
  --from-file=main.js="${repo_root}/scripts/loadgen/main.js" \
  --dry-run=client -o yaml | kubectl apply -f -

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
        - name: k6
          image: ${K6_IMAGE}
          imagePullPolicy: Always
          command:
            - k6
            - run
            - /scripts/main.js
          env:
            - name: BASE_URL
              value: ${BASE_URL}
            - name: API_BASE_URL
              value: ${API_BASE_URL}
            - name: MANIFEST_PATH
              value: /config/manifest.json
            - name: WORKLOAD
              value: ${WORKLOAD}
            - name: RUN_ID
              value: ${RUN_ID}
            - name: COOKIE_POOL_SIZE
              value: "${COOKIE_POOL_SIZE}"
            - name: SERVICE_MAP_DURATION
              value: "${SERVICE_MAP_DURATION}"
            - name: SERVICE_MAP_VUS
              value: "${SERVICE_MAP_VUS}"
            - name: SERVICE_MAP_SLEEP_MIN_SECONDS
              value: "${SERVICE_MAP_SLEEP_MIN_SECONDS}"
            - name: SERVICE_MAP_SLEEP_MAX_SECONDS
              value: "${SERVICE_MAP_SLEEP_MAX_SECONDS}"
            - name: ASSET_SERVICE_BASE_URL
              value: "${ASSET_SERVICE_BASE_URL}"
            - name: ORDER_INGEST_BASE_URL
              value: "${ORDER_INGEST_BASE_URL}"
            - name: PRICING_SERVICE_BASE_URL
              value: "${PRICING_SERVICE_BASE_URL}"
            - name: NOTIFICATION_SERVICE_BASE_URL
              value: "${NOTIFICATION_SERVICE_BASE_URL}"
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
            - name: loadgen-script
              mountPath: /scripts
              readOnly: true
      volumes:
        - name: loadgen-manifest
          configMap:
            name: ${MANIFEST_CONFIGMAP}
        - name: loadgen-script
          configMap:
            name: ${SCRIPT_CONFIGMAP}
EOF

if kubectl -n "${NAMESPACE}" wait --for=condition=Complete "job/${JOB_NAME}" --timeout="${TIMEOUT}"; then
  kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}"
  exit 0
fi

kubectl -n "${NAMESPACE}" logs "job/${JOB_NAME}" || true
kubectl -n "${NAMESPACE}" describe "job/${JOB_NAME}"
exit 1
