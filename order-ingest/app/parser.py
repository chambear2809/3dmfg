import csv
import io
from decimal import Decimal, InvalidOperation

from .models import ParseCsvResponse

ORDER_ID_COLS = ["order id", "Order ID", "order_id", "Order_ID", "Order Number", "order_number", "Order #", "Order#"]
CUSTOMER_EMAIL_COLS = ["customer email", "Customer Email", "customer_email", "Email", "email", "Buyer Email", "buyer_email"]
CUSTOMER_NAME_COLS = ["customer name", "Customer Name", "customer_name", "Name", "name", "Buyer Name", "buyer_name", "Shipping Name", "shipping name"]
PRODUCT_SKU_COLS = ["product sku", "Product SKU", "product_sku", "SKU", "sku", "Variant SKU", "variant_sku", "Item SKU", "item_sku"]
QUANTITY_COLS = ["quantity", "Quantity", "Qty", "qty", "QTY"]
UNIT_PRICE_COLS = ["unit price", "Unit Price", "unit_price", "Price", "price", "Item Price", "item_price"]
SHIPPING_COST_COLS = ["shipping cost", "Shipping Cost", "shipping_cost", "Shipping", "shipping"]
TAX_COLS = ["tax amount", "Tax Amount", "tax_amount", "Tax", "tax"]
SHIP_LINE1_COLS = ["shipping address line 1", "Shipping Address Line 1", "shipping_address_line1", "Shipping Address", "shipping address"]
SHIP_CITY_COLS = ["shipping city", "Shipping City", "shipping_city", "City", "city"]
SHIP_STATE_COLS = ["shipping state", "Shipping State", "shipping_state", "State", "state"]
SHIP_ZIP_COLS = ["shipping zip", "Shipping Zip", "shipping_zip", "Zip", "zip", "Postal Code", "postal_code"]
SHIP_COUNTRY_COLS = ["shipping country", "Shipping Country", "shipping_country", "Country", "country"]
NOTES_COLS = ["customer notes", "Customer Notes", "customer_notes", "Notes", "notes", "Order Notes"]


def clean_price(price_str: str) -> Decimal | None:
    if not price_str:
        return None
    try:
        cleaned = price_str.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return None
        return Decimal(cleaned)
    except (ValueError, TypeError, InvalidOperation):
        return None


def _find_col(row: dict, candidates: list[str]) -> str:
    for col in candidates:
        val = row.get(col, "").strip()
        if val:
            return val
    return ""


def parse_orders_from_csv(csv_text: str) -> ParseCsvResponse:
    reader = csv.DictReader(io.StringIO(csv_text))

    total_rows = 0
    errors: list[dict] = []
    orders_dict: dict[str, dict] = {}

    for row_num, row in enumerate(reader, start=2):
        total_rows += 1
        order_id = ""

        try:
            order_id = _find_col(row, ORDER_ID_COLS) or f"IMPORT-{row_num}"
            customer_email = _find_col(row, CUSTOMER_EMAIL_COLS).lower()
            if not customer_email or "@" not in customer_email:
                customer_email = f"import-{order_id.lower().replace(' ', '-')}@placeholder.local"

            product_sku = _find_col(row, PRODUCT_SKU_COLS)
            if not product_sku:
                errors.append({"row": row_num, "order_id": order_id, "error": "Product SKU missing - line item skipped"})
                continue

            quantity = 1
            qty_str = _find_col(row, QUANTITY_COLS)
            if qty_str:
                try:
                    quantity = int(float(qty_str.replace(",", "")))
                    if quantity <= 0:
                        quantity = 1
                except (ValueError, TypeError):
                    pass

            unit_price = None
            up_str = _find_col(row, UNIT_PRICE_COLS)
            if up_str:
                unit_price = clean_price(up_str)

            shipping_cost = Decimal("0.00")
            sc_str = _find_col(row, SHIPPING_COST_COLS)
            if sc_str:
                shipping_cost = clean_price(sc_str) or Decimal("0.00")

            tax_amount = Decimal("0.00")
            tax_str = _find_col(row, TAX_COLS)
            if tax_str:
                tax_amount = clean_price(tax_str) or Decimal("0.00")

            customer_name = _find_col(row, CUSTOMER_NAME_COLS)

            shipping_address: dict[str, str] = {}
            for key, cols in [
                ("line1", SHIP_LINE1_COLS),
                ("city", SHIP_CITY_COLS),
                ("state", SHIP_STATE_COLS),
                ("zip", SHIP_ZIP_COLS),
                ("country", SHIP_COUNTRY_COLS),
            ]:
                val = _find_col(row, cols)
                if val:
                    shipping_address[key] = val

            notes = _find_col(row, NOTES_COLS)

            if order_id not in orders_dict:
                orders_dict[order_id] = {
                    "source_order_id": order_id,
                    "customer_email": customer_email,
                    "customer_name": customer_name or None,
                    "shipping_address": shipping_address,
                    "shipping_cost": shipping_cost,
                    "tax_amount": tax_amount,
                    "notes": notes or None,
                    "lines": [],
                }

            orders_dict[order_id]["lines"].append(
                {
                    "sku": product_sku,
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )
        except Exception as exc:
            errors.append({"row": row_num, "order_id": order_id or None, "error": str(exc)})

    return ParseCsvResponse(
        total_rows=total_rows,
        orders=list(orders_dict.values()),
        errors=errors,
    )
