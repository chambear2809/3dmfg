from datetime import datetime, timezone
from decimal import Decimal

from app.models.sales_order import SalesOrder
from app.services import order_import_service


def _make_sales_order(db, *, order_number: str, source_order_id: str) -> SalesOrder:
    sales_order = SalesOrder(
        user_id=1,
        order_number=order_number,
        order_type="line_item",
        source="manual",
        source_order_id=source_order_id,
        product_name="Smoke Fixture",
        quantity=1,
        material_type="PLA",
        finish="standard",
        unit_price=Decimal("10.00"),
        total_price=Decimal("10.00"),
        tax_amount=Decimal("0.00"),
        shipping_cost=Decimal("0.00"),
        grand_total=Decimal("10.00"),
        status="pending",
        payment_status="pending",
        rush_level="standard",
        shipping_country="USA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(sales_order)
    db.flush()
    return sales_order


def test_generate_import_order_number_uses_highest_numeric_suffix(db):
    year = datetime.now(timezone.utc).year
    _make_sales_order(db, order_number=f"SO-{year}-000009", source_order_id="SRC-9")
    _make_sales_order(db, order_number=f"SO-{year}-000023", source_order_id="SRC-23")

    order_number = order_import_service.generate_import_order_number(db)

    assert order_number == f"SO-{year}-000024"


def test_import_normalized_orders_retries_duplicate_order_number(db, make_product, monkeypatch):
    year = datetime.now(timezone.utc).year
    existing_order = _make_sales_order(
        db,
        order_number=f"SO-{year}-000023",
        source_order_id="EXISTING-ORDER",
    )
    product = make_product(sku="IMPORT-RETRY-001", selling_price=Decimal("12.34"))

    generated_numbers = iter([
        existing_order.order_number,
        f"SO-{year}-000024",
    ])
    monkeypatch.setattr(
        order_import_service,
        "generate_import_order_number",
        lambda db_session: next(generated_numbers),
    )

    result = order_import_service.import_normalized_orders(
        db,
        parsed_orders=[
            {
                "source_order_id": "RETRY-ORDER-1",
                "customer_email": "test@filaops.dev",
                "customer_name": "Retry User",
                "shipping_address": {},
                "shipping_cost": Decimal("0.00"),
                "tax_amount": Decimal("0.00"),
                "notes": None,
                "lines": [
                    {
                        "sku": product.sku,
                        "quantity": 1,
                        "unit_price": Decimal("12.34"),
                    }
                ],
            }
        ],
        total_rows=1,
        current_user_id=1,
        create_customers=False,
        source="manual",
    )

    imported = db.query(SalesOrder).filter(SalesOrder.source_order_id == "RETRY-ORDER-1").one()

    assert result["created"] == 1
    assert result["skipped"] == 0
    assert result["errors"] == []
    assert imported.order_number == f"SO-{year}-000024"
