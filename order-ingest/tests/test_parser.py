from decimal import Decimal

from app.parser import parse_orders_from_csv


def test_parse_single_row_order():
    csv_text = (
        "Order ID,Customer Email,Customer Name,Product SKU,Quantity,Unit Price\n"
        "ORD-1,test@example.com,Jane Doe,SKU-1,2,19.99\n"
    )

    result = parse_orders_from_csv(csv_text)

    assert result.total_rows == 1
    assert result.errors == []
    assert len(result.orders) == 1
    order = result.orders[0]
    assert order.source_order_id == "ORD-1"
    assert order.customer_email == "test@example.com"
    assert order.lines[0].sku == "SKU-1"
    assert order.lines[0].quantity == 2
    assert order.lines[0].unit_price == Decimal("19.99")


def test_parse_groups_multiple_rows_by_order_id():
    csv_text = (
        "Order ID,Customer Email,Product SKU,Quantity,Unit Price\n"
        "ORD-2,group@example.com,SKU-1,1,10.00\n"
        "ORD-2,group@example.com,SKU-2,3,5.00\n"
    )

    result = parse_orders_from_csv(csv_text)

    assert result.total_rows == 2
    assert len(result.orders) == 1
    assert [line.sku for line in result.orders[0].lines] == ["SKU-1", "SKU-2"]


def test_parse_records_missing_sku_as_error():
    csv_text = (
        "Order ID,Customer Email,Quantity,Unit Price\n"
        "ORD-3,error@example.com,1,10.00\n"
    )

    result = parse_orders_from_csv(csv_text)

    assert result.total_rows == 1
    assert result.orders == []
    assert len(result.errors) == 1
    assert "Product SKU missing" in result.errors[0].error
