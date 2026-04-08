"""
Authorization boundary tests for internal ERP routers.

These endpoints are part of the admin/staff application surface and should not
be reachable with a customer account, even when the user is authenticated.
"""


class TestStaffOnlyRouters:
    """Representative internal endpoints reject customer sessions."""

    def test_customer_cannot_access_items(self, customer_client):
        response = customer_client.get("/api/v1/items")
        assert response.status_code == 403

    def test_customer_cannot_access_quotes(self, customer_client):
        response = customer_client.get("/api/v1/quotes")
        assert response.status_code == 403

    def test_customer_cannot_access_settings(self, customer_client):
        response = customer_client.get("/api/v1/settings/company")
        assert response.status_code == 403

    def test_customer_cannot_access_production_orders(self, customer_client):
        response = customer_client.get("/api/v1/production-orders/")
        assert response.status_code == 403

    def test_customer_cannot_access_purchase_orders(self, customer_client):
        response = customer_client.get("/api/v1/purchase-orders/")
        assert response.status_code == 403

    def test_customer_cannot_access_payments(self, customer_client):
        response = customer_client.get("/api/v1/payments")
        assert response.status_code == 403
