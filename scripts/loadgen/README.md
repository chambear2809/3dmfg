# Loadgen

1. Seed the benchmark dataset and manifest:

```bash
npm run loadgen:seed
```

2. Run the browser smoke before load:

```bash
npm --prefix frontend run test:load:smoke
```

3. Run the k6 workload:

```bash
npm run loadgen:k6
```

4. Run the browser smoke again after load.

The seeder owns all benchmark rows with the `LG` prefix and rewrites `scripts/loadgen/manifest.json` on each run. The k6 script logs in only during `setup()`, reuses a small cookie pool, and tags every request with `X-Request-ID=<RUN_ID>-...` plus `User-Agent=filaops-loadgen/<workload>`.

`npm run loadgen:k6` uses `scripts/loadgen/run-k6.sh`, which prefers a native `k6` binary and falls back to `grafana/k6` via Docker if `k6` is not installed locally.

`npm run loadgen:seed` uses `backend/.venv/bin/python`, so the benchmark seeder does not depend on your global Python packages.

Containerized seeding is also available:

```bash
npm run loadgen:seed:docker
```

That path runs the seeder through the existing `backend` Compose service, mounts the repo into the container at `/work`, and writes the manifest back to `scripts/loadgen/manifest.json` on the host.

Required env:

- `API_BASE_URL`: backend API root, default `http://127.0.0.1:8000/api/v1`
- `LOADGEN_ADMIN_EMAIL` / `LOADGEN_ADMIN_PASSWORD`: benchmark admin credentials
- `MANIFEST_PATH`: manifest consumed by k6
- `LOADGEN_MANIFEST_PATH`: manifest path for Playwright when running from `frontend/`
- `LOADGEN_MANIFEST_JSON`: inline manifest JSON for containerized Playwright runs
- `WORKLOAD`: `service-map`, `read`, `mixed`, `write`, or `all`
- `RUN_ID`: correlation prefix used in request IDs
- `SERVICE_MAP_DURATION`: duration for the low-rate service-map scenario, default `4m`
- `SERVICE_MAP_VUS`: VUs for the service-map scenario, default `1`

Docker fallback notes:

- If `k6` is missing locally, the wrapper uses Docker and defaults to `http://host.docker.internal:5173` and `http://host.docker.internal:8000/api/v1`
- Override `BASE_URL` and `API_BASE_URL` explicitly if your app is not reachable on those host ports

Compose stack notes:

- App stack: `docker compose up -d --build`
- Seed in container: `npm run loadgen:seed:docker`
- Run k6 against the Compose frontend/backend ports:

```bash
BASE_URL=http://host.docker.internal \
API_BASE_URL=http://host.docker.internal:8000/api/v1 \
npm run loadgen:k6
```

Kubernetes smoke notes:

- Seed the dataset in-cluster and refresh `loadgen-manifest` automatically:
  `bash k8s/3dprint/run-seed-loadgen.sh`
- Run the k6 workload in-cluster:
  `bash k8s/3dprint/run-k6-loadgen.sh`
  The Kubernetes helper now defaults to `WORKLOAD=service-map`, which routes
  traffic through `http://frontend` and exercises the CSV import path that
  drives `frontend -> backend -> order-ingest` without hammering the heavier
  dashboard endpoints. Use `WORKLOAD=all` when you explicitly want the broader
  benchmark profile.
- Build and push the Playwright runner image from `frontend/Dockerfile.playwright`
- Publish the benchmark manifest to a ConfigMap with `k8s/3dprint/create-loadgen-manifest-configmap.sh`
- Run the smoke job with `k8s/3dprint/run-playwright-smoke.sh`

Profiles:

- `small`: quick local run
- `medium`: larger local/dev benchmark
- `large`: heavier local/dev benchmark

Default workload envelopes:

- `service-map`: low-rate order import loop against `/admin/orders/import` for 4m at 1 VU
- `read`: 2m ramp, 5m steady, 1m down at 30 VUs
- `mixed`: 1m ramp, 4m steady, 1m down at 15 VUs
- `write`: 1m ramp, 3m steady, 1m down at 5 VUs

The browser smoke uses the benchmark dataset directly and does not depend on `frontend/tests/e2e/auth.setup.ts`.
