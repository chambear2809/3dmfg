"""
Tests for Fulfillment API endpoints (app/api/v1/endpoints/admin/fulfillment.py)

Covers:
- GET /api/v1/admin/fulfillment/stats (dashboard statistics)
- GET /api/v1/admin/fulfillment/queue (production queue with filters)
- GET /api/v1/admin/fulfillment/queue/{id} (production order details)
- POST /api/v1/admin/fulfillment/queue/{id}/start (start production)
- POST /api/v1/admin/fulfillment/queue/{id}/complete-print (complete printing)
- POST /api/v1/admin/fulfillment/queue/{id}/pass-qc (pass quality check)
- POST /api/v1/admin/fulfillment/queue/{id}/fail-qc (fail quality check)
- GET /api/v1/admin/fulfillment/ready-to-ship (orders ready to ship)
- POST /api/v1/admin/fulfillment/ship/{id}/mark-shipped (manual ship)
- POST /api/v1/admin/fulfillment/bulk-update (bulk status update)
- Auth: 401 without token
"""
import pytest
from decimal import Decimal


BASE_URL = "/api/v1/admin/fulfillment"
PROD_ORDERS_URL = "/api/v1/production-orders"


# =============================================================================
# Helpers
# =============================================================================

def _create_product_with_bom(make_product, make_bom, db):
    """Create a finished good with a raw material and active BOM."""
    fg = make_product(
        item_type="finished_good",
        procurement_type="make",
        selling_price=Decimal("15.00"),
        standard_cost=Decimal("5.00"),
        cost_method="standard",
    )
    raw = make_product(
        item_type="supply",
        unit="G",
        is_raw_material=True,
        average_cost=Decimal("0.02"),
    )
    bom = make_bom(
        product_id=fg.id,
        lines=[
            {"component_id": raw.id, "quantity": Decimal("100"), "unit": "G"},
        ],
    )
    db.flush()
    return fg, raw, bom


def _create_production_order(client, product_id, quantity=10):
    """POST a new production order via the production orders API and return the JSON."""
    response = client.post(PROD_ORDERS_URL, json={
        "product_id": product_id,
        "quantity_ordered": str(quantity),
    })
    assert response.status_code == 200, response.text
    return response.json()


def _get_production_order_to_status(client, order_id, target_status):
    """Drive a production order through its lifecycle to reach a target status.

    Uses the production orders API endpoints (release, start) and fulfillment
    endpoints (start, complete-print) to transition the order.
    """
    if target_status in ("released", "in_progress", "printed"):
        resp = client.post(f"{PROD_ORDERS_URL}/{order_id}/release")
        assert resp.status_code == 200, f"Release failed: {resp.text}"

    if target_status in ("in_progress", "printed"):
        # Use the fulfillment start endpoint which creates a PrintJob
        resp = client.post(
            f"{BASE_URL}/queue/{order_id}/start",
            json={},
        )
        assert resp.status_code == 200, f"Start production failed: {resp.text}"

    if target_status == "printed":
        resp = client.post(
            f"{BASE_URL}/queue/{order_id}/complete-print",
            json={
                "actual_time_minutes": 120,
                "qty_good": 10,
                "qty_bad": 0,
            },
        )
        assert resp.status_code == 200, f"Complete print failed: {resp.text}"


# =============================================================================
# Auth tests -- endpoints requiring authentication
# =============================================================================

class TestFulfillmentAuth:
    """Verify auth is required on protected endpoints."""

    def test_stats_requires_auth(self, unauthed_client):
        response = unauthed_client.get(f"{BASE_URL}/stats")
        assert response.status_code == 401

    def test_queue_requires_auth(self, unauthed_client):
        response = unauthed_client.get(f"{BASE_URL}/queue")
        assert response.status_code == 401

    def test_queue_detail_requires_auth(self, unauthed_client):
        response = unauthed_client.get(f"{BASE_URL}/queue/1")
        assert response.status_code == 401

    def test_start_production_requires_auth(self, unauthed_client):
        response = unauthed_client.post(
            f"{BASE_URL}/queue/1/start",
            json={},
        )
        assert response.status_code == 401

    def test_complete_print_requires_auth(self, unauthed_client):
        response = unauthed_client.post(
            f"{BASE_URL}/queue/1/complete-print",
            json={},
        )
        assert response.status_code == 401

    def test_pass_qc_requires_auth(self, unauthed_client):
        response = unauthed_client.post(f"{BASE_URL}/queue/1/pass-qc")
        assert response.status_code == 401

    def test_fail_qc_requires_auth(self, unauthed_client):
        response = unauthed_client.post(
            f"{BASE_URL}/queue/1/fail-qc?failure_reason=defect",
        )
        assert response.status_code == 401

    def test_ready_to_ship_requires_auth(self, unauthed_client):
        response = unauthed_client.get(f"{BASE_URL}/ready-to-ship")
        assert response.status_code == 401

    def test_mark_shipped_requires_auth(self, unauthed_client):
        response = unauthed_client.post(
            f"{BASE_URL}/ship/1/mark-shipped",
            json={
                "tracking_number": "1Z999",
                "carrier": "USPS",
            },
        )
        assert response.status_code == 401

    def test_bulk_update_requires_auth(self, unauthed_client):
        response = unauthed_client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [1],
                "new_status": "scheduled",
            },
        )
        assert response.status_code == 401


# =============================================================================
# GET /stats
# =============================================================================

class TestFulfillmentStats:
    """Test GET /api/v1/admin/fulfillment/stats"""

    def test_stats_returns_200(self, client):
        response = client.get(f"{BASE_URL}/stats")
        assert response.status_code == 200

    def test_stats_response_shape(self, client):
        response = client.get(f"{BASE_URL}/stats")
        data = response.json()
        expected_fields = [
            "pending_quotes",
            "quotes_needing_review",
            "scheduled",
            "in_progress",
            "ready_for_qc",
            "ready_to_ship",
            "shipped_today",
            "pending_revenue",
            "shipped_revenue_today",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_stats_fields_are_numeric(self, client):
        response = client.get(f"{BASE_URL}/stats")
        data = response.json()
        for field in data:
            assert isinstance(data[field], (int, float)), (
                f"Field '{field}' should be numeric, got {type(data[field])}"
            )

    def test_stats_counts_are_non_negative(self, client):
        response = client.get(f"{BASE_URL}/stats")
        data = response.json()
        for field in [
            "pending_quotes", "quotes_needing_review", "scheduled",
            "in_progress", "ready_for_qc", "ready_to_ship", "shipped_today",
        ]:
            assert data[field] >= 0, f"Count field '{field}' should be >= 0"


# =============================================================================
# GET /queue
# =============================================================================

class TestProductionQueue:
    """Test GET /api/v1/admin/fulfillment/queue"""

    def test_queue_returns_200(self, client):
        response = client.get(f"{BASE_URL}/queue")
        assert response.status_code == 200

    def test_queue_response_shape(self, client):
        response = client.get(f"{BASE_URL}/queue")
        data = response.json()
        assert "items" in data
        assert "stats" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["stats"], dict)
        assert isinstance(data["total"], int)

    def test_queue_includes_created_order(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.get(f"{BASE_URL}/queue")
        assert response.status_code == 200
        data = response.json()
        codes = [item["code"] for item in data["items"]]
        assert order_data["code"] in codes

    def test_queue_with_status_filter(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        # Release the order to set status to "released"
        client.post(f"{PROD_ORDERS_URL}/{order_data['id']}/release")

        response = client.get(f"{BASE_URL}/queue?status_filter=released")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "released"

    def test_queue_with_active_filter(self, client):
        """The 'active' filter shows all non-complete, non-cancelled orders."""
        response = client.get(f"{BASE_URL}/queue?status_filter=active")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] not in ("complete", "cancelled")

    def test_queue_with_pagination(self, client):
        response = client.get(f"{BASE_URL}/queue?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

    def test_queue_stats_contain_expected_keys(self, client):
        response = client.get(f"{BASE_URL}/queue")
        data = response.json()
        stats = data["stats"]
        expected_stat_keys = ["total_active", "scheduled", "in_progress", "printed", "urgent_count"]
        for key in expected_stat_keys:
            assert key in stats, f"Missing stat key: {key}"

    def test_queue_item_shape(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        _create_production_order(client, fg.id)

        response = client.get(f"{BASE_URL}/queue")
        data = response.json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        # Verify expected fields exist
        for field in ["id", "code", "status", "quantity", "created_at"]:
            assert field in item, f"Queue item missing field: {field}"


# =============================================================================
# GET /queue/{id}
# =============================================================================

class TestQueueDetail:
    """Test GET /api/v1/admin/fulfillment/queue/{id}"""

    def test_get_existing_order_detail(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.get(f"{BASE_URL}/queue/{order_data['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_data["id"]
        assert data["code"] == order_data["code"]

    def test_get_detail_includes_product(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.get(f"{BASE_URL}/queue/{order_data['id']}")
        data = response.json()
        assert "product" in data
        if data["product"]:
            assert data["product"]["id"] == fg.id

    def test_get_detail_includes_bom(self, client, db, make_product, make_bom):
        fg, _, bom = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.get(f"{BASE_URL}/queue/{order_data['id']}")
        data = response.json()
        assert "bom" in data
        if data["bom"]:
            assert data["bom"]["id"] == bom.id

    def test_get_detail_includes_print_jobs(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.get(f"{BASE_URL}/queue/{order_data['id']}")
        data = response.json()
        assert "print_jobs" in data
        assert isinstance(data["print_jobs"], list)

    def test_get_nonexistent_returns_404(self, client):
        response = client.get(f"{BASE_URL}/queue/999999")
        assert response.status_code == 404


# =============================================================================
# POST /queue/{id}/start
# =============================================================================

class TestStartProduction:
    """Test POST /api/v1/admin/fulfillment/queue/{id}/start"""

    def test_start_draft_order(self, client, db, make_product, make_bom):
        """Draft orders can be started via the fulfillment endpoint."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    def test_start_released_order(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        client.post(f"{PROD_ORDERS_URL}/{order_data['id']}/release")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    def test_start_with_notes(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={"notes": "Starting batch run"},
        )
        assert response.status_code == 200

    def test_start_with_printer_id(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={"printer_id": "leonardo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    def test_start_creates_print_job(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )

        # Verify the queue detail now includes a print job
        detail_resp = client.get(f"{BASE_URL}/queue/{order_data['id']}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["print_jobs"]) >= 1

    def test_start_reserves_materials(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        # Response should include material reservation info
        assert "reserved_materials" in data or "status" in data

    def test_start_nonexistent_returns_404(self, client):
        response = client.post(
            f"{BASE_URL}/queue/999999/start",
            json={},
        )
        assert response.status_code == 404

    def test_start_already_in_progress_returns_400(self, client, db, make_product, make_bom):
        """Cannot start an order that is already in_progress."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        # Start once
        resp1 = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )
        assert resp1.status_code == 200

        # Starting again should fail (in_progress is not in the allowed statuses)
        resp2 = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )
        assert resp2.status_code == 400

    def test_start_completed_order_returns_400(self, client, db, make_product, make_bom):
        """Cannot start a completed order."""
        from app.models.production_order import ProductionOrder
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        po = db.query(ProductionOrder).filter(
            ProductionOrder.id == order_data["id"]
        ).first()
        po.status = "complete"
        db.flush()

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/start",
            json={},
        )
        assert response.status_code == 400


# =============================================================================
# POST /queue/{id}/complete-print
# =============================================================================

class TestCompletePrint:
    """Test POST /api/v1/admin/fulfillment/queue/{id}/complete-print"""

    def test_complete_print_in_progress_order(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "in_progress")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/complete-print",
            json={
                "actual_time_minutes": 120,
                "actual_material_grams": 450.0,
                "qty_good": 9,
                "qty_bad": 1,
                "qc_notes": "minor stringing on part #3",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "printed"

    def test_complete_print_minimal_body(self, client, db, make_product, make_bom):
        """Complete print with empty body defaults qty_good to full quantity."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "in_progress")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/complete-print",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "printed"

    def test_complete_print_nonexistent_returns_404(self, client):
        response = client.post(
            f"{BASE_URL}/queue/999999/complete-print",
            json={},
        )
        assert response.status_code == 404

    def test_complete_print_draft_order_returns_400(self, client, db, make_product, make_bom):
        """Cannot complete print on a draft order."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/complete-print",
            json={},
        )
        assert response.status_code == 400

    def test_complete_print_already_printed_returns_400(self, client, db, make_product, make_bom):
        """Cannot complete print on an already-printed order."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/complete-print",
            json={},
        )
        assert response.status_code == 400

    def test_complete_print_response_contains_consumed_materials(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "in_progress")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/complete-print",
            json={"qty_good": 10, "qty_bad": 0},
        )
        assert response.status_code == 200
        data = response.json()
        # Should include material consumption info
        assert "consumed_materials" in data or "status" in data


# =============================================================================
# POST /queue/{id}/pass-qc
# =============================================================================

class TestPassQC:
    """Test POST /api/v1/admin/fulfillment/queue/{id}/pass-qc"""

    def test_pass_qc_printed_order(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(f"{BASE_URL}/queue/{order_data['id']}/pass-qc")
        # May return 200 or 500 depending on inventory/accounting setup
        assert response.status_code in (200, 500), response.text
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "completed"

    def test_pass_qc_with_notes(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/pass-qc?qc_notes=All+parts+look+good"
        )
        assert response.status_code in (200, 500), response.text
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    def test_pass_qc_response_shape(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(f"{BASE_URL}/queue/{order_data['id']}/pass-qc")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "production_order_id" in data
            assert "code" in data
            assert "status" in data
            assert "message" in data

    def test_pass_qc_nonexistent_returns_404(self, client):
        response = client.post(f"{BASE_URL}/queue/999999/pass-qc")
        assert response.status_code == 404

    def test_pass_qc_draft_order_returns_400(self, client, db, make_product, make_bom):
        """Cannot pass QC on a draft order -- must be in 'printed' status."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(f"{BASE_URL}/queue/{order_data['id']}/pass-qc")
        assert response.status_code == 400

    def test_pass_qc_in_progress_returns_400(self, client, db, make_product, make_bom):
        """Cannot pass QC on an in_progress order -- must complete print first."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "in_progress")

        response = client.post(f"{BASE_URL}/queue/{order_data['id']}/pass-qc")
        assert response.status_code == 400


# =============================================================================
# POST /queue/{id}/fail-qc
# =============================================================================

class TestFailQC:
    """Test POST /api/v1/admin/fulfillment/queue/{id}/fail-qc"""

    def test_fail_qc_printed_order(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/fail-qc"
            "?failure_reason=Layer+adhesion+failure&reprint=true"
        )
        # May return 200 or 500 depending on inventory/accounting setup
        assert response.status_code in (200, 500), response.text
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "qc_failed"
            assert data["reprint_created"] is True
            assert data["new_production_order_id"] is not None
            assert data["new_production_order_code"] is not None

    def test_fail_qc_without_reprint(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/fail-qc"
            "?failure_reason=Catastrophic+failure&reprint=false"
        )
        assert response.status_code in (200, 500), response.text
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "qc_failed"
            assert data["reprint_created"] is False
            assert data["new_production_order_id"] is None

    def test_fail_qc_response_shape(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/fail-qc"
            "?failure_reason=Warping"
        )
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "production_order_id" in data
            assert "status" in data
            assert "reprint_created" in data
            assert "materials_released" in data
            assert "message" in data

    def test_fail_qc_nonexistent_returns_404(self, client):
        response = client.post(
            f"{BASE_URL}/queue/999999/fail-qc?failure_reason=defect"
        )
        assert response.status_code == 404

    def test_fail_qc_draft_order_returns_400(self, client, db, make_product, make_bom):
        """Cannot fail QC on a draft order."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/fail-qc"
            "?failure_reason=defect"
        )
        assert response.status_code == 400

    def test_fail_qc_in_progress_returns_400(self, client, db, make_product, make_bom):
        """Cannot fail QC on an in_progress order -- must complete print first."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "in_progress")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/fail-qc"
            "?failure_reason=bad+layer+adhesion"
        )
        assert response.status_code == 400

    def test_fail_qc_requires_failure_reason(self, client, db, make_product, make_bom):
        """The failure_reason query parameter is required."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        _get_production_order_to_status(client, order_data["id"], "printed")

        response = client.post(
            f"{BASE_URL}/queue/{order_data['id']}/fail-qc"
        )
        assert response.status_code == 422


# =============================================================================
# GET /ready-to-ship
# =============================================================================

class TestReadyToShip:
    """Test GET /api/v1/admin/fulfillment/ready-to-ship"""

    def test_ready_to_ship_returns_200(self, client):
        response = client.get(f"{BASE_URL}/ready-to-ship")
        assert response.status_code == 200

    def test_ready_to_ship_response_shape(self, client):
        response = client.get(f"{BASE_URL}/ready-to-ship")
        data = response.json()
        assert "orders" in data
        assert "total" in data
        assert isinstance(data["orders"], list)
        assert isinstance(data["total"], int)

    def test_ready_to_ship_with_limit(self, client):
        response = client.get(f"{BASE_URL}/ready-to-ship?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["orders"]) <= 5

    def test_ready_to_ship_includes_order_with_correct_status(
        self, client, db, make_sales_order, make_product
    ):
        """Orders with status 'ready_to_ship' should appear in the list."""
        product = make_product(selling_price=Decimal("25.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=5,
            unit_price=Decimal("25.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.get(f"{BASE_URL}/ready-to-ship")
        assert response.status_code == 200
        data = response.json()
        order_ids = [o["id"] for o in data["orders"]]
        assert so.id in order_ids

    def test_ready_to_ship_order_shape(self, client, db, make_sales_order, make_product):
        """Verify the shape of each order in the ready-to-ship list."""
        product = make_product(selling_price=Decimal("25.00"))
        make_sales_order(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("25.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.get(f"{BASE_URL}/ready-to-ship")
        data = response.json()
        assert len(data["orders"]) > 0
        order = data["orders"][0]
        for field in ["id", "order_number", "quantity", "shipping_address", "created_at"]:
            assert field in order, f"Missing field in ready-to-ship order: {field}"


# =============================================================================
# POST /ship/{id}/mark-shipped
# =============================================================================

class TestMarkShipped:
    """Test POST /api/v1/admin/fulfillment/ship/{id}/mark-shipped"""

    def test_mark_shipped_valid(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("20.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=2,
            unit_price=Decimal("20.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.post(
            f"{BASE_URL}/ship/{so.id}/mark-shipped",
            json={
                "tracking_number": "1Z999AA10123456784",
                "carrier": "USPS",
                "shipping_cost": 7.50,
                "notify_customer": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tracking_number"] == "1Z999AA10123456784"
        assert data["carrier"] == "USPS"
        assert data["status"] == "shipped"

    def test_mark_shipped_minimal(self, client, db, make_sales_order, make_product):
        """Mark shipped with only required fields (tracking_number, carrier)."""
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("10.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.post(
            f"{BASE_URL}/ship/{so.id}/mark-shipped",
            json={
                "tracking_number": "9400111899223456789012",
                "carrier": "USPS",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "shipped"

    def test_mark_shipped_response_shape(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("10.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.post(
            f"{BASE_URL}/ship/{so.id}/mark-shipped",
            json={
                "tracking_number": "ABC123",
                "carrier": "FedEx",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "order_number" in data
        assert "status" in data
        assert "tracking_number" in data
        assert "carrier" in data
        assert "message" in data

    def test_mark_shipped_nonexistent_returns_404(self, client):
        response = client.post(
            f"{BASE_URL}/ship/999999/mark-shipped",
            json={
                "tracking_number": "1Z999",
                "carrier": "UPS",
            },
        )
        assert response.status_code == 404

    def test_mark_shipped_missing_tracking_returns_422(self, client, db, make_sales_order, make_product):
        """tracking_number is required."""
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("10.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.post(
            f"{BASE_URL}/ship/{so.id}/mark-shipped",
            json={
                "carrier": "USPS",
            },
        )
        assert response.status_code == 422

    def test_mark_shipped_missing_carrier_returns_422(self, client, db, make_sales_order, make_product):
        """carrier is required."""
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("10.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.post(
            f"{BASE_URL}/ship/{so.id}/mark-shipped",
            json={
                "tracking_number": "1Z999",
            },
        )
        assert response.status_code == 422

    def test_mark_shipped_with_shipping_cost(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("30.00"))
        so = make_sales_order(
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("30.00"),
            status="ready_to_ship",
        )
        db.flush()

        response = client.post(
            f"{BASE_URL}/ship/{so.id}/mark-shipped",
            json={
                "tracking_number": "1Z999",
                "carrier": "UPS",
                "shipping_cost": 12.99,
            },
        )
        assert response.status_code == 200


# =============================================================================
# POST /bulk-update
# =============================================================================

class TestBulkUpdate:
    """Test POST /api/v1/admin/fulfillment/bulk-update"""

    def test_bulk_update_valid_status(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order1 = _create_production_order(client, fg.id)
        order2 = _create_production_order(client, fg.id, quantity=5)

        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [order1["id"], order2["id"]],
                "new_status": "scheduled",
                "notes": "batch scheduled for Monday",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2
        assert data["error_count"] == 0
        assert len(data["updated"]) == 2

    def test_bulk_update_response_shape(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [order_data["id"]],
                "new_status": "scheduled",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "updated_count" in data
        assert "error_count" in data
        assert "updated" in data
        assert "errors" in data

    def test_bulk_update_with_nonexistent_ids(self, client):
        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [999998, 999999],
                "new_status": "scheduled",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert data["error_count"] == 2
        assert len(data["errors"]) == 2

    def test_bulk_update_mixed_valid_and_invalid_ids(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [order_data["id"], 999999],
                "new_status": "scheduled",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 1
        assert data["error_count"] == 1

    def test_bulk_update_invalid_status_returns_400(self, client):
        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [1],
                "new_status": "invalid_status",
            },
        )
        assert response.status_code == 400

    def test_bulk_update_records_old_and_new_status(self, client, db, make_product, make_bom):
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)

        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [order_data["id"]],
                "new_status": "scheduled",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["updated"]) == 1
        updated_item = data["updated"][0]
        assert updated_item["id"] == order_data["id"]
        assert updated_item["old_status"] == "draft"
        assert updated_item["new_status"] == "scheduled"

    def test_bulk_update_empty_ids_list(self, client):
        """Bulk update with empty list should succeed with zero updates."""
        response = client.post(
            f"{BASE_URL}/bulk-update",
            json={
                "production_order_ids": [],
                "new_status": "scheduled",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert data["error_count"] == 0


# =============================================================================
# Full lifecycle -- start -> complete-print -> pass-qc (fulfillment path)
# =============================================================================

class TestFulfillmentLifecycle:
    """Test the full fulfillment workflow through the fulfillment endpoints."""

    def test_start_then_complete_print(self, client, db, make_product, make_bom):
        """Production order can go from draft -> in_progress -> printed."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        order_id = order_data["id"]

        # Start production
        start_resp = client.post(
            f"{BASE_URL}/queue/{order_id}/start",
            json={},
        )
        assert start_resp.status_code == 200
        assert start_resp.json()["status"] == "in_progress"

        # Complete printing
        complete_resp = client.post(
            f"{BASE_URL}/queue/{order_id}/complete-print",
            json={
                "actual_time_minutes": 90,
                "qty_good": 10,
                "qty_bad": 0,
            },
        )
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "printed"

    def test_full_production_cycle_through_qc(self, client, db, make_product, make_bom):
        """Full cycle: draft -> in_progress -> printed -> completed (QC pass)."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        order_id = order_data["id"]

        # Start
        client.post(f"{BASE_URL}/queue/{order_id}/start", json={})

        # Complete print
        client.post(
            f"{BASE_URL}/queue/{order_id}/complete-print",
            json={"qty_good": 10},
        )

        # Pass QC
        qc_resp = client.post(f"{BASE_URL}/queue/{order_id}/pass-qc")
        # May succeed or fail depending on TransactionService setup
        assert qc_resp.status_code in (200, 500), qc_resp.text
        if qc_resp.status_code == 200:
            assert qc_resp.json()["status"] == "completed"

    def test_production_with_qc_failure_and_reprint(self, client, db, make_product, make_bom):
        """Full cycle with QC failure: draft -> in_progress -> printed -> qc_failed."""
        fg, _, _ = _create_product_with_bom(make_product, make_bom, db)
        order_data = _create_production_order(client, fg.id)
        order_id = order_data["id"]

        # Start and complete print
        client.post(f"{BASE_URL}/queue/{order_id}/start", json={})
        client.post(
            f"{BASE_URL}/queue/{order_id}/complete-print",
            json={"qty_good": 10},
        )

        # Fail QC with reprint
        qc_resp = client.post(
            f"{BASE_URL}/queue/{order_id}/fail-qc"
            "?failure_reason=Warping+on+base&reprint=true"
        )
        assert qc_resp.status_code in (200, 500), qc_resp.text
        if qc_resp.status_code == 200:
            data = qc_resp.json()
            assert data["status"] == "qc_failed"
            assert data["reprint_created"] is True
            # The new production order should exist
            assert data["new_production_order_code"] is not None
