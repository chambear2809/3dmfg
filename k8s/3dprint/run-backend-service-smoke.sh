#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-3dprint}"
BACKEND_TARGET="${BACKEND_TARGET:-deploy/backend}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
ASSET_SERVICE_BASE_URL="${ASSET_SERVICE_BASE_URL:-}"
ORDER_INGEST_BASE_URL="${ORDER_INGEST_BASE_URL:-}"
ORDER_IMPORT_SKU="${ORDER_IMPORT_SKU:-}"
MODE="${MODE:-full}"
RUN_ID="${RUN_ID:-}"
EXPECT_ORDER_IMPORT_STATUS="${EXPECT_ORDER_IMPORT_STATUS:-200}"

kubectl -n "${NAMESPACE}" get "${BACKEND_TARGET}" >/dev/null

kubectl -n "${NAMESPACE}" exec -i "${BACKEND_TARGET}" -- env \
  SMOKE_BACKEND_BASE_URL="${BACKEND_BASE_URL}" \
  SMOKE_ASSET_SERVICE_BASE_URL="${ASSET_SERVICE_BASE_URL}" \
  SMOKE_ORDER_INGEST_BASE_URL="${ORDER_INGEST_BASE_URL}" \
  SMOKE_ORDER_IMPORT_SKU="${ORDER_IMPORT_SKU}" \
  SMOKE_MODE="${MODE}" \
  SMOKE_RUN_ID="${RUN_ID}" \
  SMOKE_EXPECT_ORDER_IMPORT_STATUS="${EXPECT_ORDER_IMPORT_STATUS}" \
  python - <<'PY'
import json
import os
import time
import uuid

import requests

from app.db.session import SessionLocal
from app.models.product import Product

timeout = 30
backend_base_url = os.environ.get("SMOKE_BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
asset_service_base_url = (
    os.environ.get("SMOKE_ASSET_SERVICE_BASE_URL")
    or os.environ.get("ASSET_SERVICE_URL")
    or "http://asset-service"
).rstrip("/")
order_ingest_base_url = (
    os.environ.get("SMOKE_ORDER_INGEST_BASE_URL")
    or os.environ.get("ORDER_INGEST_SERVICE_URL")
    or "http://order-ingest"
).rstrip("/")
mode = (os.environ.get("SMOKE_MODE") or "full").strip() or "full"
run_id = (os.environ.get("SMOKE_RUN_ID") or "").strip() or uuid.uuid4().hex
expected_order_import_status = int(
    (os.environ.get("SMOKE_EXPECT_ORDER_IMPORT_STATUS") or "200").strip()
)
admin_email = (os.environ.get("DEMO_ADMIN_EMAIL") or "").strip()
admin_password = (os.environ.get("DEMO_ADMIN_PASSWORD") or "").strip()
request_counter = 0

if not admin_email or not admin_password:
    raise SystemExit("Missing DEMO_ADMIN_EMAIL or DEMO_ADMIN_PASSWORD in environment")


def expect_success(response, label):
    if not response.ok:
        raise SystemExit(
            f"{label} failed with status {response.status_code}: {response.text[:500]}"
        )
    return response


def expect_status(response, label, expected_status):
    if response.status_code != expected_status:
        raise SystemExit(
            f"{label} failed with status {response.status_code}; "
            f"expected {expected_status}: {response.text[:500]}"
        )
    return response


def response_json(response):
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:500]}


def next_headers(label):
    global request_counter
    request_counter += 1
    return {
        "User-Agent": f"filaops-backend-smoke/{mode}",
        "X-Request-ID": f"{run_id}-{label}-{request_counter}",
    }


def plain_request(method, url, label, *, timeout_seconds=timeout, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers.update(next_headers(label))
    return requests.request(method, url, timeout=timeout_seconds, headers=headers, **kwargs)


def session_request(method, url, label, *, timeout_seconds=timeout, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers.update(next_headers(label))
    return session.request(method, url, timeout=timeout_seconds, headers=headers, **kwargs)


def resolve_order_import_sku():
    override = (os.environ.get("SMOKE_ORDER_IMPORT_SKU") or "").strip()
    if override:
        return override

    db = SessionLocal()
    try:
        product = (
            db.query(Product)
            .filter(Product.active.is_(True), Product.item_type == "finished_good")
            .order_by(Product.id)
            .first()
        )
        if product is None:
            product = db.query(Product).filter(Product.active.is_(True)).order_by(Product.id).first()
        if product is None:
            raise SystemExit("No active product found for order import smoke test")
        return product.sku
    finally:
        db.close()


summary = {
    "mode": mode,
    "run_id": run_id,
    "expected_order_import_status": expected_order_import_status,
}
session = requests.Session()

backend_health = expect_success(
    plain_request("GET", f"{backend_base_url}/health", "backend-health"),
    "backend health check",
)

summary["backend_health"] = {
    "status": backend_health.status_code,
    "body": response_json(backend_health),
}

if mode == "full":
    asset_health = expect_success(
        plain_request("GET", f"{asset_service_base_url}/health", "asset-health"),
        "asset service health check",
    )
    order_ingest_health = expect_success(
        plain_request("GET", f"{order_ingest_base_url}/health", "order-ingest-health"),
        "order ingest health check",
    )
    summary["asset_service_health"] = {
        "status": asset_health.status_code,
        "body": response_json(asset_health),
    }
    summary["order_ingest_health"] = {
        "status": order_ingest_health.status_code,
        "body": response_json(order_ingest_health),
    }

login = expect_success(
    session_request(
        "POST",
        f"{backend_base_url}/api/v1/auth/login",
        "backend-login",
        data={"username": admin_email, "password": admin_password},
    ),
    "backend login",
)
cookies = sorted(session.cookies.get_dict().keys())
if "access_token" not in cookies or "refresh_token" not in cookies:
    raise SystemExit(f"Login succeeded but expected auth cookies were missing: {cookies}")
summary["auth"] = {
    "status": login.status_code,
    "cookies": cookies,
}

if mode == "full":
    payload = f"asset-smoke-{run_id}".encode("ascii")
    upload = expect_success(
        session_request(
            "POST",
            f"{backend_base_url}/api/v1/admin/uploads/product-image",
            "asset-upload",
            files={"file": ("smoke.png", payload, "image/png")},
        ),
        "asset upload via backend",
    )
    upload_data = upload.json()
    asset_key = upload_data["filename"]
    asset_url = upload_data["url"]

    fetch = expect_success(
        session_request(
            "GET",
            f"{backend_base_url}{asset_url}",
            "asset-fetch",
        ),
        "asset fetch via backend",
    )
    if fetch.content != payload:
        raise SystemExit("Fetched asset content did not match uploaded payload")
    content_type = fetch.headers.get("content-type", "")
    if not content_type.startswith("image/png"):
        raise SystemExit(f"Unexpected asset content type: {content_type}")

    delete = expect_success(
        session_request(
            "DELETE",
            f"{backend_base_url}/api/v1/admin/uploads/product-image/{asset_key}",
            "asset-delete",
        ),
        "asset delete via backend",
    )

    fetch_after_delete = session_request(
        "GET",
        f"{backend_base_url}{asset_url}",
        "asset-fetch-deleted",
    )
    if fetch_after_delete.status_code != 404:
        raise SystemExit(
            f"Expected deleted asset fetch to return 404, got {fetch_after_delete.status_code}"
        )

    summary["asset_flow"] = {
        "upload": upload_data,
        "fetch_status": fetch.status_code,
        "delete_status": delete.status_code,
        "fetch_after_delete_status": fetch_after_delete.status_code,
    }

order_import_sku = resolve_order_import_sku()
order_id = f"SMOKE-{int(time.time())}"
csv_text = (
    "Order ID,Customer Email,Customer Name,Product SKU,Quantity,Unit Price\n"
    f"{order_id},smoke+{run_id}@example.com,Smoke Test,{order_import_sku},1,12.34\n"
)
order_import = expect_status(
    session_request(
        "POST",
        f"{backend_base_url}/api/v1/admin/orders/import",
        "order-import",
        params={"create_customers": "true", "source": "manual"},
        files={"file": ("orders.csv", csv_text.encode("utf-8"), "text/csv")},
        timeout_seconds=60,
    ),
    "order import via backend",
    expected_order_import_status,
)
summary["order_import"] = {
    "status": order_import.status_code,
    "sku": order_import_sku,
    "result": response_json(order_import),
}

if order_import.ok:
    order_import_data = order_import.json()
    if order_import_data.get("created") != 1:
        raise SystemExit(f"Unexpected order import result: {order_import_data}")

print(json.dumps(summary, indent=2, sort_keys=True))
PY
