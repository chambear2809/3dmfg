# MicroK8s Local Deployment

Local Kubernetes deployment of FilaOps on MicroK8s. All images are built
locally and imported directly into MicroK8s -- no container registry or cloud
dependencies required.

## Prerequisites

| Requirement | Minimum | Install |
|-------------|---------|---------|
| MicroK8s | 1.28+ | `sudo snap install microk8s --classic` |
| Docker | 20.10+ | https://docs.docker.com/get-docker/ |
| RAM | 8 GB | (4 GB usable by MicroK8s) |
| CPU | 4 cores | |
| Disk | 20 GB free | |

After installing MicroK8s:

```bash
sudo usermod -aG microk8s $USER
newgrp microk8s
microk8s start
```

## Quick Start

```bash
./k8s/microk8s/deploy.sh deploy
```

This single command will:

1. Verify MicroK8s is running
2. Enable required addons (`dns`, `hostpath-storage`)
3. Build all 6 Docker images from source
4. Import images into MicroK8s
5. Create the `3dprint` namespace and demo secrets
6. Apply all Kubernetes manifests
7. Wait for rollouts to complete

Once finished, the app is available at **http://localhost:30080**.

Default demo credentials (from `create-demo-secret.sh`):

- Email: `admin@example.com`
- Password: `C1sco12345`

## Commands

```
./k8s/microk8s/deploy.sh deploy    # Full build + deploy
./k8s/microk8s/deploy.sh status    # Show pods, services, PVCs
./k8s/microk8s/deploy.sh rebuild   # Rebuild images + restart pods
./k8s/microk8s/deploy.sh teardown  # Delete everything
```

## Architecture

```
Browser ──► frontend (NodePort 30080)
              │
              ├── /api/* ──► backend ──► PostgreSQL
              │                 │
              │                 ├──► asset-service ──► PVC (file storage)
              │                 ├──► order-ingest ──► pricing-service
              │                 └──► notification-service
              │
              └── /* ──► static SPA assets
```

All services run in the `3dprint` namespace. Inter-service communication uses
Kubernetes DNS (e.g., `http://backend`, `http://asset-service`).

## What differs from k8s/3dprint

| Aspect | k8s/3dprint (AWS/demo) | k8s/microk8s (local) |
|--------|------------------------|----------------------|
| StorageClass | `gp2` (EBS) | `microk8s-hostpath` |
| Images | Private ECR | Locally built (`*:local`) |
| Frontend access | `LoadBalancer` (ELB) | `NodePort 30080` |
| OpenTelemetry | Operator + Splunk Collector | Disabled |
| Microservices | ConfigMap bundles + `pip install` at startup | Docker images with baked-in deps |
| CORS origins | AWS ELB hostname | `localhost:30080` |
| Splunk RUM | Enabled | Disabled |

## Troubleshooting

### Pods stuck in Pending

Check if the hostpath-storage addon is enabled:

```bash
microk8s status
microk8s enable hostpath-storage
```

Verify PVCs are bound:

```bash
microk8s kubectl -n 3dprint get pvc
```

### ImagePullBackOff

Images must be imported into MicroK8s, not pulled from a registry. Re-run:

```bash
./k8s/microk8s/deploy.sh rebuild
```

### Backend CrashLoopBackOff

The backend waits for PostgreSQL via its startup probe. Check if the `db`
StatefulSet is healthy first:

```bash
microk8s kubectl -n 3dprint logs statefulset/db
microk8s kubectl -n 3dprint get pods -l app=db
```

### Port 30080 not reachable

Verify the frontend service has the NodePort assigned:

```bash
microk8s kubectl -n 3dprint get svc frontend
```

On Linux with MicroK8s installed via snap, `localhost:30080` should work
directly. On macOS (via Multipass VM), you may need the VM IP:

```bash
multipass info microk8s-vm | grep IPv4
```

### Resetting everything

```bash
./k8s/microk8s/deploy.sh teardown
./k8s/microk8s/deploy.sh deploy
```

This deletes the namespace (including PVCs and data) and redeploys from
scratch.
