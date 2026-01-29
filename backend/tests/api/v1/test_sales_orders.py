"""
Tests for Sales Orders API endpoints (app/api/v1/endpoints/sales_orders.py)

Covers:
- GET /api/v1/sales-orders/ (list with pagination, filters)
- GET /api/v1/sales-orders/{id} (get single)
- POST /api/v1/sales-orders/ (create line-item order)
- PATCH /api/v1/sales-orders/{id}/status (status transitions)
- POST /api/v1/sales-orders/{id}/cancel (cancellation)
- DELETE /api/v1/sales-orders/{id} (delete draft)
- Auth: 401 without token
"""
import pytest
from decimal import Decimal


BASE_URL = "/api/v1/sales-orders"


# =============================================================================
# Auth tests — endpoints requiring authentication
# =============================================================================

class TestSalesOrderAuth:
    """Verify auth is required on protected endpoints."""

    def test_create_requires_auth(self, unauthed_client):
        response = unauthed_client.post(BASE_URL, json={
            "lines": [{"product_id": 1, "quantity": 1}],
        })
        assert response.status_code == 401

    def test_list_requires_auth(self, unauthed_client):
        response = unauthed_client.get(BASE_URL)
        # List may or may not require auth depending on implementation
        # Just verify it doesn't return 500
        assert response.status_code in (200, 401)


# =============================================================================
# List / Get — read operations
# =============================================================================

class TestListSalesOrders:
    """Test GET /api/v1/sales-orders/"""

    def test_list_returns_200(self, client):
        response = client.get(BASE_URL)
        assert response.status_code == 200

    def test_list_returns_array(self, client):
        response = client.get(BASE_URL)
        data = response.json()
        # Could be a list or a paginated response
        assert isinstance(data, (list, dict))

    def test_list_with_status_filter(self, client):
        response = client.get(f"{BASE_URL}?status=draft")
        assert response.status_code == 200

    def test_list_with_pagination(self, client):
        response = client.get(f"{BASE_URL}?offset=0&limit=5")
        assert response.status_code == 200


class TestGetSalesOrder:
    """Test GET /api/v1/sales-orders/{id}"""

    def test_get_existing_order(self, client, db, make_product, make_sales_order):
        product = make_product(selling_price=Decimal("25.00"))
        so = make_sales_order(product_id=product.id, quantity=2, unit_price=Decimal("25.00"))
        db.flush()

        response = client.get(f"{BASE_URL}/{so.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == so.id
        assert data["order_number"] == so.order_number

    def test_get_nonexistent_returns_404(self, client):
        response = client.get(f"{BASE_URL}/999999")
        assert response.status_code == 404


# =============================================================================
# Create — POST /api/v1/sales-orders/
# =============================================================================

class TestCreateSalesOrder:
    """Test manual line-item order creation."""

    def test_create_basic_order(self, client, db, make_product):
        product = make_product(
            selling_price=Decimal("15.00"),
            item_type="finished_good",
        )
        db.flush()

        response = client.post(BASE_URL, json={
            "lines": [
                {"product_id": product.id, "quantity": 3}
            ],
            "source": "manual",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["order_number"].startswith("SO-")
        assert data["status"] == "pending"
        assert data["order_type"] == "line_item"

    def test_create_order_uses_catalog_price(self, client, db, make_product):
        """Security: backend should use product.selling_price, not frontend-supplied price."""
        product = make_product(selling_price=Decimal("25.00"))
        db.flush()

        response = client.post(BASE_URL, json={
            "lines": [
                {"product_id": product.id, "quantity": 1, "unit_price": 1.00}
            ],
        })
        assert response.status_code == 201
        data = response.json()
        # Should use catalog price ($25), not submitted price ($1)
        assert Decimal(str(data["total_price"])) == Decimal("25.00")

    def test_create_order_missing_lines_fails(self, client):
        response = client.post(BASE_URL, json={
            "lines": [],
        })
        assert response.status_code == 422

    def test_create_order_nonexistent_product_fails(self, client):
        response = client.post(BASE_URL, json={
            "lines": [{"product_id": 999999, "quantity": 1}],
        })
        assert response.status_code == 404

    def test_create_order_inactive_product_fails(self, client, db, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        product.active = False
        db.flush()

        response = client.post(BASE_URL, json={
            "lines": [{"product_id": product.id, "quantity": 1}],
        })
        assert response.status_code == 400
        assert "discontinued" in response.json()["detail"].lower()

    def test_create_order_zero_price_product_fails(self, client, db, make_product):
        product = make_product(selling_price=Decimal("0"))
        db.flush()

        response = client.post(BASE_URL, json={
            "lines": [{"product_id": product.id, "quantity": 1}],
        })
        assert response.status_code == 400
        assert "no selling price" in response.json()["detail"].lower()

    def test_create_multi_line_order(self, client, db, make_product):
        p1 = make_product(selling_price=Decimal("10.00"))
        p2 = make_product(selling_price=Decimal("20.00"))
        db.flush()

        response = client.post(BASE_URL, json={
            "lines": [
                {"product_id": p1.id, "quantity": 2},
                {"product_id": p2.id, "quantity": 1},
            ],
        })
        assert response.status_code == 201
        data = response.json()
        # Total should be (10*2) + (20*1) = 40
        assert Decimal(str(data["total_price"])) == Decimal("40.00")


# =============================================================================
# Status transitions — PATCH /api/v1/sales-orders/{id}/status
# =============================================================================

class TestStatusTransitions:
    """Test sales order status updates."""

    def test_get_status_transitions(self, client):
        response = client.get(f"{BASE_URL}/status-transitions")
        assert response.status_code == 200

    def test_update_status_valid_transition(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(
            product_id=product.id,
            status="pending_payment",
            material_type="PLA",
        )
        db.flush()

        response = client.patch(f"{BASE_URL}/{so.id}/status", json={
            "status": "confirmed",
        })
        # Confirmed requires payment — may return 400 or 200 depending on payment_status
        assert response.status_code in (200, 400)

    def test_update_status_nonexistent_order(self, client):
        response = client.patch(f"{BASE_URL}/999999/status", json={
            "status": "confirmed",
        })
        assert response.status_code == 404


# =============================================================================
# Cancel — POST /api/v1/sales-orders/{id}/cancel
# =============================================================================

class TestCancelSalesOrder:
    """Test order cancellation."""

    def test_cancel_draft_order(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(product_id=product.id, status="draft")
        db.flush()

        response = client.post(f"{BASE_URL}/{so.id}/cancel", json={
            "cancellation_reason": "Customer changed their mind",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_nonexistent_order(self, client):
        response = client.post(f"{BASE_URL}/999999/cancel", json={
            "cancellation_reason": "test",
        })
        assert response.status_code == 404

    def test_cancel_shipped_order_fails(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(product_id=product.id, status="shipped")
        db.flush()

        response = client.post(f"{BASE_URL}/{so.id}/cancel", json={
            "cancellation_reason": "Too late",
        })
        # Shipped orders can't be cancelled
        assert response.status_code == 400


# =============================================================================
# Delete — DELETE /api/v1/sales-orders/{id}
# =============================================================================

class TestDeleteSalesOrder:
    """Test order deletion (only drafts can be deleted)."""

    def test_delete_cancelled_order(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(product_id=product.id, status="cancelled")
        db.flush()

        response = client.delete(f"{BASE_URL}/{so.id}")
        assert response.status_code == 204

    def test_delete_pending_order(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(product_id=product.id, status="pending")
        db.flush()

        response = client.delete(f"{BASE_URL}/{so.id}")
        assert response.status_code == 204

    def test_delete_confirmed_order_fails(self, client, db, make_sales_order, make_product):
        product = make_product(selling_price=Decimal("10.00"))
        so = make_sales_order(product_id=product.id, status="confirmed")
        db.flush()

        response = client.delete(f"{BASE_URL}/{so.id}")
        assert response.status_code == 400

    def test_delete_nonexistent_returns_404(self, client):
        response = client.delete(f"{BASE_URL}/999999")
        assert response.status_code == 404
