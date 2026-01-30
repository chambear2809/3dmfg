"""
Tests for the admin dashboard API endpoints.

Covers:
- Authentication (401 without token)
- Response shape and field types for all endpoints
- Period parameter variations for trend endpoints
- Numeric field non-negativity
- Stats reflecting test data where feasible
"""
import pytest
from decimal import Decimal


BASE = "/api/v1/admin/dashboard"

TREND_PERIODS = ["WTD", "MTD", "QTD", "YTD", "ALL"]


# =============================================================================
# Authentication
# =============================================================================

class TestDashboardAuth:
    """All dashboard endpoints require staff authentication."""

    ENDPOINTS = [
        f"{BASE}/",
        f"{BASE}/summary",
        f"{BASE}/recent-orders",
        f"{BASE}/pending-bom-reviews",
        f"{BASE}/sales-trend",
        f"{BASE}/shipping-trend",
        f"{BASE}/production-trend",
        f"{BASE}/purchasing-trend",
        f"{BASE}/stats",
        f"{BASE}/modules",
        f"{BASE}/profit-summary",
    ]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_unauthenticated_returns_401(self, unauthed_client, endpoint):
        response = unauthed_client.get(endpoint)
        assert response.status_code == 401


# =============================================================================
# GET /api/v1/admin/dashboard/ — Full dashboard
# =============================================================================

class TestFullDashboard:
    """Tests for the full dashboard endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/")
        assert response.status_code == 200

    def test_response_has_top_level_keys(self, client):
        data = client.get(f"{BASE}/").json()
        assert "summary" in data
        assert "modules" in data
        assert "recent_orders" in data
        assert "pending_bom_reviews" in data

    def test_summary_has_all_fields(self, client):
        summary = client.get(f"{BASE}/").json()["summary"]
        expected_fields = [
            "pending_quotes",
            "quotes_today",
            "pending_orders",
            "orders_needing_review",
            "orders_in_production",
            "orders_ready_to_ship",
            "active_production_orders",
            "boms_needing_review",
            "revenue_30_days",
            "orders_30_days",
        ]
        for field in expected_fields:
            assert field in summary, f"Missing summary field: {field}"

    def test_summary_numeric_fields_are_non_negative(self, client):
        summary = client.get(f"{BASE}/").json()["summary"]
        int_fields = [
            "pending_quotes",
            "quotes_today",
            "pending_orders",
            "orders_needing_review",
            "orders_in_production",
            "orders_ready_to_ship",
            "active_production_orders",
            "boms_needing_review",
            "orders_30_days",
        ]
        for field in int_fields:
            assert isinstance(summary[field], int), f"{field} should be int"
            assert summary[field] >= 0, f"{field} should be non-negative"

        # revenue_30_days may be a string decimal or float
        revenue = summary["revenue_30_days"]
        assert float(revenue) >= 0

    def test_modules_is_list_of_objects(self, client):
        modules = client.get(f"{BASE}/").json()["modules"]
        assert isinstance(modules, list)
        assert len(modules) > 0
        for mod in modules:
            assert "name" in mod
            assert "description" in mod
            assert "route" in mod
            assert "icon" in mod

    def test_recent_orders_is_list(self, client):
        data = client.get(f"{BASE}/").json()
        assert isinstance(data["recent_orders"], list)

    def test_pending_bom_reviews_is_list(self, client):
        data = client.get(f"{BASE}/").json()
        assert isinstance(data["pending_bom_reviews"], list)


# =============================================================================
# GET /api/v1/admin/dashboard/summary — Module-organized stats
# =============================================================================

class TestDashboardSummary:
    """Tests for the module-organized summary endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/summary")
        assert response.status_code == 200

    def test_response_has_all_sections(self, client):
        data = client.get(f"{BASE}/summary").json()
        for section in ["quotes", "orders", "production", "boms", "inventory", "revenue"]:
            assert section in data, f"Missing section: {section}"

    def test_quotes_section_fields(self, client):
        quotes = client.get(f"{BASE}/summary").json()["quotes"]
        assert "pending" in quotes
        assert "this_week" in quotes
        assert isinstance(quotes["pending"], int)
        assert isinstance(quotes["this_week"], int)

    def test_orders_section_fields(self, client):
        orders = client.get(f"{BASE}/summary").json()["orders"]
        for field in ["confirmed", "in_production", "ready_to_ship", "overdue"]:
            assert field in orders, f"Missing orders field: {field}"
            assert isinstance(orders[field], int)
            assert orders[field] >= 0

    def test_production_section_fields(self, client):
        production = client.get(f"{BASE}/summary").json()["production"]
        for field in ["in_progress", "scheduled", "ready_to_start"]:
            assert field in production, f"Missing production field: {field}"
            assert isinstance(production[field], int)
            assert production[field] >= 0

    def test_boms_section_fields(self, client):
        boms = client.get(f"{BASE}/summary").json()["boms"]
        assert "needs_review" in boms
        assert "active" in boms
        assert isinstance(boms["needs_review"], int)
        assert isinstance(boms["active"], int)

    def test_inventory_section_fields(self, client):
        inventory = client.get(f"{BASE}/summary").json()["inventory"]
        assert "low_stock_count" in inventory
        assert "active_orders" in inventory
        assert isinstance(inventory["low_stock_count"], int)
        assert isinstance(inventory["active_orders"], int)

    def test_revenue_section_fields(self, client):
        revenue = client.get(f"{BASE}/summary").json()["revenue"]
        assert "last_30_days" in revenue
        assert "orders_last_30_days" in revenue
        assert float(revenue["last_30_days"]) >= 0
        assert isinstance(revenue["orders_last_30_days"], int)


# =============================================================================
# GET /api/v1/admin/dashboard/recent-orders
# =============================================================================

class TestRecentOrders:
    """Tests for the recent orders endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/recent-orders")
        assert response.status_code == 200

    def test_returns_list(self, client):
        data = client.get(f"{BASE}/recent-orders").json()
        assert isinstance(data, list)

    def test_default_limit_is_5(self, client, make_sales_order):
        for i in range(7):
            make_sales_order(status="confirmed")

        data = client.get(f"{BASE}/recent-orders").json()
        assert len(data) <= 5

    def test_custom_limit(self, client, make_sales_order):
        for i in range(4):
            make_sales_order(status="confirmed")

        data = client.get(f"{BASE}/recent-orders?limit=3").json()
        assert len(data) <= 3

    def test_order_fields_present(self, client, make_sales_order):
        make_sales_order(status="confirmed")
        data = client.get(f"{BASE}/recent-orders?limit=1").json()
        assert len(data) >= 1

        order = data[0]
        expected_fields = [
            "id",
            "order_number",
            "product_name",
            "customer_name",
            "status",
            "payment_status",
            "grand_total",
            "total_price",
            "created_at",
        ]
        for field in expected_fields:
            assert field in order, f"Missing order field: {field}"

    def test_order_field_types(self, client, make_sales_order):
        make_sales_order(status="confirmed", unit_price=Decimal("25.00"), quantity=2)
        data = client.get(f"{BASE}/recent-orders?limit=1").json()
        order = data[0]

        assert isinstance(order["id"], int)
        assert isinstance(order["order_number"], str)
        assert isinstance(order["status"], str)
        assert isinstance(order["grand_total"], (int, float))
        assert order["grand_total"] >= 0


# =============================================================================
# GET /api/v1/admin/dashboard/pending-bom-reviews
# =============================================================================

class TestPendingBomReviews:
    """Tests for the pending BOM reviews endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/pending-bom-reviews")
        assert response.status_code == 200

    def test_returns_list(self, client):
        data = client.get(f"{BASE}/pending-bom-reviews").json()
        assert isinstance(data, list)

    def test_default_limit_is_5(self, client, make_product, make_bom):
        for i in range(7):
            product = make_product()
            make_bom(product_id=product.id, active=True)

        data = client.get(f"{BASE}/pending-bom-reviews").json()
        assert len(data) <= 5

    def test_bom_review_fields_present(self, client, make_product, make_bom):
        product = make_product()
        make_bom(product_id=product.id, active=True)

        data = client.get(f"{BASE}/pending-bom-reviews?limit=1").json()
        assert len(data) >= 1

        bom = data[0]
        expected_fields = ["id", "code", "name", "total_cost", "line_count", "created_at"]
        for field in expected_fields:
            assert field in bom, f"Missing BOM field: {field}"

    def test_bom_review_field_types(self, client, make_product, make_bom):
        product = make_product()
        component = make_product(item_type="supply")
        make_bom(
            product_id=product.id,
            active=True,
            lines=[{"component_id": component.id, "quantity": Decimal("100"), "unit": "G"}],
        )

        data = client.get(f"{BASE}/pending-bom-reviews?limit=1").json()
        bom = data[0]

        assert isinstance(bom["id"], int)
        assert isinstance(bom["line_count"], int)
        assert bom["line_count"] >= 0


# =============================================================================
# GET /api/v1/admin/dashboard/sales-trend
# =============================================================================

class TestSalesTrend:
    """Tests for the sales trend endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/sales-trend")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get(f"{BASE}/sales-trend").json()
        expected_fields = [
            "period",
            "start_date",
            "end_date",
            "total_revenue",
            "total_orders",
            "total_payments",
            "total_payment_count",
            "data",
        ]
        for field in expected_fields:
            assert field in data, f"Missing sales-trend field: {field}"

    def test_default_period_is_mtd(self, client):
        data = client.get(f"{BASE}/sales-trend").json()
        assert data["period"] == "MTD"

    @pytest.mark.parametrize("period", TREND_PERIODS)
    def test_period_variations(self, client, period):
        response = client.get(f"{BASE}/sales-trend?period={period}")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == period

    def test_numeric_totals_non_negative(self, client):
        data = client.get(f"{BASE}/sales-trend").json()
        assert data["total_revenue"] >= 0
        assert data["total_orders"] >= 0
        assert data["total_payments"] >= 0
        assert data["total_payment_count"] >= 0

    def test_data_is_list(self, client):
        data = client.get(f"{BASE}/sales-trend").json()
        assert isinstance(data["data"], list)

    def test_data_point_fields(self, client, make_sales_order):
        make_sales_order(status="confirmed")
        data = client.get(f"{BASE}/sales-trend?period=MTD").json()

        if len(data["data"]) > 0:
            point = data["data"][0]
            assert "date" in point
            assert "total" in point
            assert "sales" in point
            assert "orders" in point
            assert "payments" in point
            assert "payment_count" in point


# =============================================================================
# GET /api/v1/admin/dashboard/shipping-trend
# =============================================================================

class TestShippingTrend:
    """Tests for the shipping trend endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/shipping-trend")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get(f"{BASE}/shipping-trend").json()
        expected_fields = [
            "period",
            "start_date",
            "end_date",
            "total_shipped",
            "total_value",
            "pipeline_ready",
            "pipeline_packaging",
            "data",
        ]
        for field in expected_fields:
            assert field in data, f"Missing shipping-trend field: {field}"

    def test_default_period_is_mtd(self, client):
        data = client.get(f"{BASE}/shipping-trend").json()
        assert data["period"] == "MTD"

    @pytest.mark.parametrize("period", TREND_PERIODS)
    def test_period_variations(self, client, period):
        response = client.get(f"{BASE}/shipping-trend?period={period}")
        assert response.status_code == 200
        assert response.json()["period"] == period

    def test_numeric_totals_non_negative(self, client):
        data = client.get(f"{BASE}/shipping-trend").json()
        assert data["total_shipped"] >= 0
        assert data["total_value"] >= 0
        assert data["pipeline_ready"] >= 0
        assert data["pipeline_packaging"] >= 0

    def test_data_is_list(self, client):
        data = client.get(f"{BASE}/shipping-trend").json()
        assert isinstance(data["data"], list)


# =============================================================================
# GET /api/v1/admin/dashboard/production-trend
# =============================================================================

class TestProductionTrend:
    """Tests for the production trend endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/production-trend")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get(f"{BASE}/production-trend").json()
        expected_fields = [
            "period",
            "start_date",
            "end_date",
            "total_completed",
            "total_units",
            "pipeline_in_progress",
            "pipeline_scheduled",
            "data",
        ]
        for field in expected_fields:
            assert field in data, f"Missing production-trend field: {field}"

    def test_default_period_is_mtd(self, client):
        data = client.get(f"{BASE}/production-trend").json()
        assert data["period"] == "MTD"

    @pytest.mark.parametrize("period", TREND_PERIODS)
    def test_period_variations(self, client, period):
        response = client.get(f"{BASE}/production-trend?period={period}")
        assert response.status_code == 200
        assert response.json()["period"] == period

    def test_numeric_totals_non_negative(self, client):
        data = client.get(f"{BASE}/production-trend").json()
        assert data["total_completed"] >= 0
        assert data["total_units"] >= 0
        assert data["pipeline_in_progress"] >= 0
        assert data["pipeline_scheduled"] >= 0

    def test_data_is_list(self, client):
        data = client.get(f"{BASE}/production-trend").json()
        assert isinstance(data["data"], list)


# =============================================================================
# GET /api/v1/admin/dashboard/purchasing-trend
# =============================================================================

class TestPurchasingTrend:
    """Tests for the purchasing trend endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/purchasing-trend")
        assert response.status_code == 200

    def test_response_shape(self, client):
        data = client.get(f"{BASE}/purchasing-trend").json()
        expected_fields = [
            "period",
            "start_date",
            "end_date",
            "total_received",
            "total_spend",
            "pipeline_ordered",
            "pipeline_draft",
            "pending_spend",
            "data",
        ]
        for field in expected_fields:
            assert field in data, f"Missing purchasing-trend field: {field}"

    def test_default_period_is_mtd(self, client):
        data = client.get(f"{BASE}/purchasing-trend").json()
        assert data["period"] == "MTD"

    @pytest.mark.parametrize("period", TREND_PERIODS)
    def test_period_variations(self, client, period):
        response = client.get(f"{BASE}/purchasing-trend?period={period}")
        assert response.status_code == 200
        assert response.json()["period"] == period

    def test_numeric_totals_non_negative(self, client):
        data = client.get(f"{BASE}/purchasing-trend").json()
        assert data["total_received"] >= 0
        assert data["total_spend"] >= 0
        assert data["pipeline_ordered"] >= 0
        assert data["pipeline_draft"] >= 0
        assert data["pending_spend"] >= 0

    def test_data_is_list(self, client):
        data = client.get(f"{BASE}/purchasing-trend").json()
        assert isinstance(data["data"], list)


# =============================================================================
# GET /api/v1/admin/dashboard/stats — Quick stats
# =============================================================================

class TestQuickStats:
    """Tests for the quick stats endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/stats")
        assert response.status_code == 200

    def test_response_has_all_fields(self, client):
        data = client.get(f"{BASE}/stats").json()
        for field in ["pending_quotes", "pending_orders", "ready_to_ship"]:
            assert field in data, f"Missing stats field: {field}"

    def test_all_fields_are_non_negative_integers(self, client):
        data = client.get(f"{BASE}/stats").json()
        for field in ["pending_quotes", "pending_orders", "ready_to_ship"]:
            assert isinstance(data[field], int)
            assert data[field] >= 0

    def test_stats_reflect_created_orders(self, client, make_sales_order):
        make_sales_order(status="confirmed")
        make_sales_order(status="confirmed")
        make_sales_order(status="ready_to_ship")

        data = client.get(f"{BASE}/stats").json()
        assert data["pending_orders"] >= 2
        assert data["ready_to_ship"] >= 1


# =============================================================================
# GET /api/v1/admin/dashboard/modules — Admin modules
# =============================================================================

class TestModules:
    """Tests for the admin modules list endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/modules")
        assert response.status_code == 200

    def test_returns_list(self, client):
        data = client.get(f"{BASE}/modules").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_module_fields_present(self, client):
        modules = client.get(f"{BASE}/modules").json()
        for mod in modules:
            assert "name" in mod
            assert "key" in mod
            assert "description" in mod
            assert "api_route" in mod
            assert "icon" in mod

    def test_module_field_types(self, client):
        modules = client.get(f"{BASE}/modules").json()
        for mod in modules:
            assert isinstance(mod["name"], str)
            assert isinstance(mod["key"], str)
            assert isinstance(mod["description"], str)
            assert isinstance(mod["api_route"], str)
            assert isinstance(mod["icon"], str)

    def test_known_modules_present(self, client):
        modules = client.get(f"{BASE}/modules").json()
        keys = [m["key"] for m in modules]
        for expected_key in ["bom", "orders", "production", "shipping", "inventory"]:
            assert expected_key in keys, f"Expected module key '{expected_key}' not found"


# =============================================================================
# GET /api/v1/admin/dashboard/profit-summary
# =============================================================================

class TestProfitSummary:
    """Tests for the profit summary endpoint."""

    def test_returns_200(self, client):
        response = client.get(f"{BASE}/profit-summary")
        assert response.status_code == 200

    def test_response_has_all_fields(self, client):
        data = client.get(f"{BASE}/profit-summary").json()
        expected_fields = [
            "revenue_this_month",
            "revenue_ytd",
            "cogs_this_month",
            "cogs_ytd",
            "gross_profit_this_month",
            "gross_profit_ytd",
            "gross_margin_percent_this_month",
            "gross_margin_percent_ytd",
            "note",
        ]
        for field in expected_fields:
            assert field in data, f"Missing profit-summary field: {field}"

    def test_revenue_and_cogs_types(self, client):
        data = client.get(f"{BASE}/profit-summary").json()
        # Pydantic serializes Decimal as string in JSON; may also be number
        for field in [
            "revenue_this_month",
            "revenue_ytd",
            "cogs_this_month",
            "cogs_ytd",
            "gross_profit_this_month",
            "gross_profit_ytd",
        ]:
            value = data[field]
            assert isinstance(value, (int, float, str)), (
                f"{field} should be numeric or string-encoded decimal"
            )
            assert float(value) is not None

    def test_margin_percent_nullable(self, client):
        data = client.get(f"{BASE}/profit-summary").json()
        # Margin percent can be None when revenue is zero
        margin_month = data["gross_margin_percent_this_month"]
        margin_ytd = data["gross_margin_percent_ytd"]
        if margin_month is not None:
            assert float(margin_month) is not None
        if margin_ytd is not None:
            assert float(margin_ytd) is not None

    def test_note_is_string_or_none(self, client):
        data = client.get(f"{BASE}/profit-summary").json()
        note = data["note"]
        assert note is None or isinstance(note, str)

    def test_gross_profit_calculation_consistency(self, client):
        data = client.get(f"{BASE}/profit-summary").json()
        revenue_month = float(data["revenue_this_month"])
        cogs_month = float(data["cogs_this_month"])
        gross_profit_month = float(data["gross_profit_this_month"])

        # gross_profit = revenue - cogs (allow small float tolerance)
        assert abs(gross_profit_month - (revenue_month - cogs_month)) < 0.01

        revenue_ytd = float(data["revenue_ytd"])
        cogs_ytd = float(data["cogs_ytd"])
        gross_profit_ytd = float(data["gross_profit_ytd"])
        assert abs(gross_profit_ytd - (revenue_ytd - cogs_ytd)) < 0.01
