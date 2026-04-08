"""
Seed benchmark data for the loadgen harness.

This script is intentionally self-contained:
- Refuses production-like targets by default
- Cleans only benchmark-owned rows
- Ensures an admin account exists for the harness
- Seeds a realistic synthetic dataset
- Writes a manifest JSON consumed by k6 and Playwright smoke tests
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Add backend/ so imports resolve as app.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.bom import BOM, BOMLine
from app.models.company_settings import CompanySettings
from app.models.inventory import Inventory, InventoryLocation
from app.models.invoice import Invoice, InvoiceLine
from app.models.item_category import ItemCategory
from app.models.manufacturing import Resource, Routing, RoutingOperation, RoutingOperationMaterial
from app.models.order_event import OrderEvent
from app.models.product import Product
from app.models.production_order import (
    ProductionOrder,
    ProductionOrderOperation,
    ProductionOrderOperationMaterial,
)
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.purchasing_event import PurchasingEvent
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.shipping_event import ShippingEvent
from app.models.user import PasswordResetRequest, RefreshToken, User
from app.models.vendor import Vendor
from app.models.work_center import WorkCenter
from app.services import invoice_service, purchase_order_service, sales_order_service
from scripts.seed_example_data import ensure_categories_exist, seed_uoms


PROFILE_CONFIGS = {
    "small": {
        "customers": 4,
        "extra_orders": 12,
    },
    "medium": {
        "customers": 10,
        "extra_orders": 40,
    },
    "large": {
        "customers": 24,
        "extra_orders": 120,
    },
}


@dataclass
class OrderLineSpec:
    product: Product
    quantity: int


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def storage_unit_cost(product: Product) -> Decimal:
    base_cost = product.standard_cost or product.average_cost or product.last_cost or Decimal("0")
    factor = Decimal(str(product.purchase_factor or 1))
    if factor <= 0:
        factor = Decimal("1")
    return Decimal(str(base_cost)) / factor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed loadgen benchmark data and write a manifest.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_CONFIGS.keys()),
        default="small",
        help="Benchmark dataset size profile.",
    )
    parser.add_argument(
        "--manifest",
        default="scripts/loadgen/manifest.json",
        help="Path to the manifest JSON to write.",
    )
    parser.add_argument(
        "--tag",
        default="LG",
        help="Benchmark entity prefix used for cleanup and manifest tagging.",
    )
    parser.add_argument(
        "--admin-email",
        default="loadgen-admin@filaops.local",
        help="Admin email used by the loadgen harness.",
    )
    parser.add_argument(
        "--admin-password",
        default="LoadgenPass123!",
        help="Admin password used by the loadgen harness.",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Override the production safety check.",
    )
    return parser.parse_args()


def assert_safe_target(allow_production: bool) -> None:
    if allow_production:
        return

    environment = (settings.ENVIRONMENT or "").lower()
    db_name = (settings.DB_NAME or "").lower()
    db_url = (settings.DATABASE_URL or settings.database_url or "").lower()
    blocked = any(token in f"{db_name} {db_url}" for token in ("prod", "production"))

    if settings.is_production or blocked:
        raise RuntimeError(
            "Refusing to seed benchmark data against a production-like target. "
            "Use --allow-production only if you have intentionally verified the database."
        )


def ensure_company_settings(db) -> None:
    settings_row = db.query(CompanySettings).filter(CompanySettings.id == 1).first()
    if settings_row:
        return

    settings_row = CompanySettings(
        id=1,
        company_name="FilaOps Benchmark",
        company_country="USA",
        company_email="benchmark@filaops.local",
        currency_code="USD",
        locale="en-US",
        timezone="America/New_York",
        invoice_prefix="INV",
        tax_enabled=False,
    )
    db.add(settings_row)
    db.flush()


def ensure_admin_user(db, email: str, password: str, tag: str) -> User:
    admin = db.query(User).filter(User.email == email).first()
    if admin:
        if admin.account_type != "admin":
            raise RuntimeError(f"User {email} exists but is not an admin.")
        admin.password_hash = hash_password(password)
        admin.status = "active"
        admin.email_verified = True
        admin.first_name = admin.first_name or tag
        admin.last_name = admin.last_name or "Loadgen"
        db.flush()
        return admin

    admin = User(
        email=email,
        password_hash=hash_password(password),
        email_verified=True,
        first_name=tag,
        last_name="Loadgen",
        company_name="FilaOps Benchmark",
        status="active",
        account_type="admin",
    )
    db.add(admin)
    db.flush()
    return admin


def get_category(db, code: str) -> ItemCategory:
    category = db.query(ItemCategory).filter(ItemCategory.code == code).first()
    if not category:
        raise RuntimeError(f"Required item category {code} was not found after seeding.")
    return category


def create_inventory_record(
    db,
    *,
    product: Product,
    location: InventoryLocation,
    on_hand: Decimal,
    allocated: Decimal = Decimal("0"),
) -> Inventory:
    record = Inventory(
        product_id=product.id,
        location_id=location.id,
        on_hand_quantity=on_hand,
        allocated_quantity=allocated,
        last_counted=now_utc(),
    )
    db.add(record)
    db.flush()
    return record


def create_product(
    db,
    *,
    sku: str,
    name: str,
    description: str,
    item_type: str,
    procurement_type: str,
    category_id: int,
    unit: str,
    standard_cost: Decimal,
    selling_price: Decimal | None = None,
    purchase_uom: str | None = None,
    purchase_factor: Decimal | None = None,
    preferred_vendor_id: int | None = None,
    reorder_point: Decimal | None = None,
    safety_stock: Decimal | None = None,
    stocking_policy: str = "on_demand",
    is_raw_material: bool = False,
    has_bom: bool = False,
) -> Product:
    product = Product(
        sku=sku,
        name=name,
        description=description,
        item_type=item_type,
        procurement_type=procurement_type,
        category_id=category_id,
        unit=unit,
        purchase_uom=purchase_uom or unit,
        purchase_factor=purchase_factor,
        standard_cost=standard_cost,
        average_cost=standard_cost,
        last_cost=standard_cost,
        selling_price=selling_price,
        preferred_vendor_id=preferred_vendor_id,
        reorder_point=reorder_point,
        safety_stock=safety_stock or Decimal("0"),
        stocking_policy=stocking_policy,
        is_raw_material=is_raw_material,
        has_bom=has_bom,
        active=True,
        type="standard",
        is_public=False,
        sales_channel="internal",
    )
    db.add(product)
    db.flush()
    return product


def create_vendor(db, *, code: str, name: str, lead_time_days: int, notes: str) -> Vendor:
    vendor = Vendor(
        code=code,
        name=name,
        contact_name="Benchmark Supply",
        email=f"{code.lower()}@filaops.local",
        phone="555-0100",
        payment_terms="Net 30",
        lead_time_days=lead_time_days,
        rating=Decimal("4.50"),
        notes=notes,
        is_active=True,
    )
    db.add(vendor)
    db.flush()
    return vendor


def create_location(db, *, code: str, name: str) -> InventoryLocation:
    location = InventoryLocation(
        code=code,
        name=name,
        type="warehouse",
        active=True,
    )
    db.add(location)
    db.flush()
    return location


def create_work_center(db, *, code: str, name: str, center_type: str, hourly_rate: Decimal) -> WorkCenter:
    work_center = WorkCenter(
        code=code,
        name=name,
        center_type=center_type,
        hourly_rate=hourly_rate,
        machine_rate_per_hour=hourly_rate,
        labor_rate_per_hour=Decimal("12.00"),
        overhead_rate_per_hour=Decimal("8.00"),
        is_active=True,
    )
    db.add(work_center)
    db.flush()
    return work_center


def create_resource(
    db,
    *,
    work_center: WorkCenter,
    code: str,
    name: str,
    status: str = "available",
    machine_type: str | None = None,
    printer_class: str | None = None,
) -> Resource:
    resource = Resource(
        work_center_id=work_center.id,
        code=code,
        name=name,
        status=status,
        machine_type=machine_type,
        printer_class=printer_class,
        is_active=True,
    )
    db.add(resource)
    db.flush()
    return resource


def create_bom(
    db,
    *,
    product: Product,
    code: str,
    name: str,
    lines: list[tuple[Product, Decimal, str, str]],
) -> BOM:
    bom = BOM(
        product_id=product.id,
        code=code,
        name=name,
        version=1,
        revision="1.0",
        active=True,
        effective_date=date.today(),
    )
    db.add(bom)
    db.flush()

    total_cost = Decimal("0")
    for sequence, (component, quantity, unit, consume_stage) in enumerate(lines, start=10):
        bom_line = BOMLine(
            bom_id=bom.id,
            component_id=component.id,
            sequence=sequence,
            quantity=quantity,
            unit=unit,
            consume_stage=consume_stage,
            is_cost_only=False,
            scrap_factor=Decimal("0"),
        )
        db.add(bom_line)
        total_cost += quantity * storage_unit_cost(component)

    bom.total_cost = total_cost
    product.has_bom = True
    db.flush()
    return bom


def create_routing(
    db,
    *,
    product: Product,
    code: str,
    name: str,
    operations: list[dict],
) -> Routing:
    routing = Routing(
        product_id=product.id,
        code=code,
        name=name,
        version=1,
        revision="1.0",
        is_active=True,
        effective_date=date.today(),
    )
    db.add(routing)
    db.flush()

    created_ops: list[RoutingOperation] = []
    for operation_data in operations:
        materials = operation_data.pop("materials", [])
        operation = RoutingOperation(
            routing_id=routing.id,
            **operation_data,
        )
        db.add(operation)
        db.flush()
        created_ops.append(operation)

        for material in materials:
            row = RoutingOperationMaterial(
                routing_operation_id=operation.id,
                component_id=material["component"].id,
                quantity=material["quantity"],
                quantity_per=material.get("quantity_per", "unit"),
                unit=material["unit"],
                scrap_factor=material.get("scrap_factor", Decimal("0")),
                is_cost_only=False,
                is_optional=False,
                is_variable=False,
                notes=material.get("notes"),
            )
            db.add(row)

    db.flush()
    routing.operations = created_ops
    routing.recalculate_totals()
    db.flush()
    return routing


def create_customer_users(db, *, count: int, tag: str) -> list[User]:
    customers: list[User] = []
    email_prefix = tag.lower()
    for index in range(1, count + 1):
        first_name = f"{tag}Customer{index:02d}"
        customer = User(
            email=f"{email_prefix}-cust-{index:02d}@filaops.local",
            password_hash=hash_password("UnusedCustPass123!"),
            email_verified=True,
            first_name=first_name,
            last_name="Benchmark",
            company_name=f"{tag} Benchmark Customer {index:02d}",
            phone=f"555-01{index:02d}",
            status="active",
            account_type="customer",
            shipping_address_line1=f"{100 + index} Benchmark Way",
            shipping_city="Atlanta",
            shipping_state="GA",
            shipping_zip=f"303{index:02d}",
            shipping_country="USA",
            billing_address_line1=f"{100 + index} Benchmark Way",
            billing_city="Atlanta",
            billing_state="GA",
            billing_zip=f"303{index:02d}",
            billing_country="USA",
            payment_terms="net30" if index % 2 == 0 else "cod",
        )
        db.add(customer)
        db.flush()
        customers.append(customer)
    return customers


def order_customer_fields(order: SalesOrder, customer: User) -> None:
    order.customer_id = customer.id
    order.customer_name = customer.company_name or customer.full_name
    order.customer_email = customer.email
    order.customer_phone = customer.phone


def create_sales_order_seed(
    db,
    *,
    slug: str,
    customer: User,
    lines: list[OrderLineSpec],
    admin: User,
    tag: str,
) -> SalesOrder:
    order = sales_order_service.create_sales_order(
        db,
        customer_id=customer.id,
        lines=[
            {
                "product_id": spec.product.id,
                "quantity": Decimal(spec.quantity),
            }
            for spec in lines
        ],
        source="loadgen",
        source_order_id=f"{tag}-{slug}",
        shipping_cost=Decimal("8.50"),
        customer_notes=f"{tag} benchmark order {slug}",
        internal_notes=f"[{tag}] benchmark seed {slug}",
        created_by_user_id=admin.id,
    )
    order_customer_fields(order, customer)
    order.estimated_completion_date = now_utc() + timedelta(days=2)
    db.flush()
    return order


def set_order_line_quantities(
    order: SalesOrder,
    *,
    allocations: dict[int, Decimal] | None = None,
    shipments: dict[int, Decimal] | None = None,
) -> None:
    allocations = allocations or {}
    shipments = shipments or {}
    for line in order.lines:
        line.allocated_quantity = allocations.get(line.product_id or -1, Decimal("0"))
        line.shipped_quantity = shipments.get(line.product_id or -1, Decimal("0"))


def get_production_orders_for_order(db, order: SalesOrder) -> list[ProductionOrder]:
    return (
        db.query(ProductionOrder)
        .filter(ProductionOrder.sales_order_id == order.id)
        .order_by(ProductionOrder.id)
        .all()
    )


def create_purchase_order_seed(
    db,
    *,
    vendor: Vendor,
    items: list[tuple[Product, Decimal, Decimal]],
    notes: str,
    status: str,
    order_days_ago: int,
    expected_days_ahead: int,
) -> PurchaseOrder:
    po = PurchaseOrder(
        po_number=purchase_order_service.generate_po_number(db),
        vendor_id=vendor.id,
        status=status,
        order_date=date.today() - timedelta(days=order_days_ago),
        expected_date=date.today() + timedelta(days=expected_days_ahead),
        subtotal=Decimal("0"),
        tax_amount=Decimal("0"),
        shipping_cost=Decimal("0"),
        total_amount=Decimal("0"),
        notes=notes,
        created_by="loadgen",
    )
    db.add(po)
    db.flush()

    subtotal = Decimal("0")
    for line_number, (product, quantity, unit_cost) in enumerate(items, start=1):
        line_total = quantity * unit_cost
        line = PurchaseOrderLine(
            purchase_order_id=po.id,
            product_id=product.id,
            line_number=line_number,
            quantity_ordered=quantity,
            quantity_received=Decimal("0"),
            purchase_unit=product.purchase_uom or product.unit,
            unit_cost=unit_cost,
            line_total=line_total,
            notes=notes,
        )
        db.add(line)
        subtotal += line_total

    po.subtotal = subtotal
    po.total_amount = subtotal
    db.flush()
    return po


def manifest_product(product: Product) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "procurement_type": product.procurement_type,
        "item_type": product.item_type,
    }


def manifest_order(order: SalesOrder) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "source_order_id": order.source_order_id,
    }


def purge_loadgen_data(db, *, tag: str, admin_email: str) -> None:
    tag_prefix = f"{tag}-%"
    customer_email_prefix = f"{tag.lower()}-cust-%@filaops.local"

    product_ids = [
        product_id
        for (product_id,) in db.query(Product.id).filter(Product.sku.like(tag_prefix)).all()
    ]
    vendor_ids = [
        vendor_id
        for (vendor_id,) in db.query(Vendor.id).filter(Vendor.code.like(tag_prefix)).all()
    ]
    user_ids = [
        user_id
        for (user_id,) in db.query(User.id)
        .filter(User.email.like(customer_email_prefix), User.email != admin_email)
        .all()
    ]
    order_ids = [
        order_id
        for (order_id,) in db.query(SalesOrder.id)
        .filter(
            (SalesOrder.source == "loadgen")
            | (SalesOrder.source_order_id.like(tag_prefix))
            | (SalesOrder.internal_notes.like(f"%[{tag}]%"))
        )
        .all()
    ]
    po_ids = [
        po_id
        for (po_id,) in db.query(PurchaseOrder.id)
        .filter(
            (PurchaseOrder.vendor_id.in_(vendor_ids) if vendor_ids else PurchaseOrder.id == -1)
            | (PurchaseOrder.notes.like(f"%[{tag}]%"))
            | (PurchaseOrder.notes.like(f"%{tag} benchmark%"))
        )
        .all()
    ]
    production_order_ids = [
        po_id
        for (po_id,) in db.query(ProductionOrder.id)
        .filter(
            (ProductionOrder.sales_order_id.in_(order_ids) if order_ids else ProductionOrder.id == -1)
            | (ProductionOrder.product_id.in_(product_ids) if product_ids else ProductionOrder.id == -1)
            | (ProductionOrder.notes.like(f"%[{tag}]%"))
        )
        .all()
    ]
    invoice_ids = [
        invoice_id
        for (invoice_id,) in db.query(Invoice.id)
        .filter(Invoice.sales_order_id.in_(order_ids) if order_ids else Invoice.id == -1)
        .all()
    ]

    if production_order_ids:
        op_ids = [
            op_id
            for (op_id,) in db.query(ProductionOrderOperation.id)
            .filter(ProductionOrderOperation.production_order_id.in_(production_order_ids))
            .all()
        ]
        if op_ids:
            db.query(ProductionOrderOperationMaterial).filter(
                ProductionOrderOperationMaterial.production_order_operation_id.in_(op_ids)
            ).delete(synchronize_session=False)
        db.query(ProductionOrderOperation).filter(
            ProductionOrderOperation.production_order_id.in_(production_order_ids)
        ).delete(synchronize_session=False)
        db.query(ProductionOrder).filter(
            ProductionOrder.id.in_(production_order_ids)
        ).delete(synchronize_session=False)

    if invoice_ids:
        db.query(InvoiceLine).filter(InvoiceLine.invoice_id.in_(invoice_ids)).delete(
            synchronize_session=False
        )
        db.query(Invoice).filter(Invoice.id.in_(invoice_ids)).delete(synchronize_session=False)

    if po_ids:
        db.query(PurchasingEvent).filter(PurchasingEvent.purchase_order_id.in_(po_ids)).delete(
            synchronize_session=False
        )
        db.query(PurchaseOrderLine).filter(PurchaseOrderLine.purchase_order_id.in_(po_ids)).delete(
            synchronize_session=False
        )
        db.query(PurchaseOrder).filter(PurchaseOrder.id.in_(po_ids)).delete(synchronize_session=False)

    if order_ids:
        db.query(ShippingEvent).filter(ShippingEvent.sales_order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.query(OrderEvent).filter(OrderEvent.sales_order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.query(SalesOrderLine).filter(SalesOrderLine.sales_order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.query(SalesOrder).filter(SalesOrder.id.in_(order_ids)).delete(synchronize_session=False)

    if product_ids:
        routing_ids = [
            routing_id
            for (routing_id,) in db.query(Routing.id).filter(Routing.product_id.in_(product_ids)).all()
        ]
        if routing_ids:
            routing_op_ids = [
                op_id
                for (op_id,) in db.query(RoutingOperation.id)
                .filter(RoutingOperation.routing_id.in_(routing_ids))
                .all()
            ]
            if routing_op_ids:
                db.query(RoutingOperationMaterial).filter(
                    RoutingOperationMaterial.routing_operation_id.in_(routing_op_ids)
                ).delete(synchronize_session=False)
            db.query(RoutingOperation).filter(RoutingOperation.routing_id.in_(routing_ids)).delete(
                synchronize_session=False
            )
            db.query(Routing).filter(Routing.id.in_(routing_ids)).delete(synchronize_session=False)

        bom_ids = [
            bom_id
            for (bom_id,) in db.query(BOM.id).filter(BOM.product_id.in_(product_ids)).all()
        ]
        if bom_ids:
            db.query(BOMLine).filter(BOMLine.bom_id.in_(bom_ids)).delete(synchronize_session=False)
            db.query(BOM).filter(BOM.id.in_(bom_ids)).delete(synchronize_session=False)

        db.query(Inventory).filter(Inventory.product_id.in_(product_ids)).delete(synchronize_session=False)
        db.query(Product).filter(Product.id.in_(product_ids)).delete(synchronize_session=False)

    if vendor_ids:
        db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).delete(synchronize_session=False)

    work_center_ids = [
        work_center_id
        for (work_center_id,) in db.query(WorkCenter.id).filter(WorkCenter.code.like(tag_prefix)).all()
    ]
    if work_center_ids:
        db.query(Resource).filter(Resource.work_center_id.in_(work_center_ids)).delete(
            synchronize_session=False
        )
        db.query(WorkCenter).filter(WorkCenter.id.in_(work_center_ids)).delete(synchronize_session=False)

    location_ids = [
        location_id
        for (location_id,) in db.query(InventoryLocation.id).filter(InventoryLocation.code.like(tag_prefix)).all()
    ]
    if location_ids:
        db.query(InventoryLocation).filter(InventoryLocation.id.in_(location_ids)).delete(
            synchronize_session=False
        )

    if user_ids:
        db.query(RefreshToken).filter(RefreshToken.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(PasswordResetRequest).filter(PasswordResetRequest.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    db.flush()


def seed_dataset(db, *, profile: str, tag: str, admin: User) -> dict:
    config = PROFILE_CONFIGS[profile]
    ensure_company_settings(db)
    seed_uoms(db)
    ensure_categories_exist(db)
    db.flush()

    purge_loadgen_data(db, tag=tag, admin_email=admin.email)
    db.flush()

    categories = {
        code: get_category(db, code)
        for code in (
            "PLA",
            "BOXES",
            "INSERTS",
            "STANDARD_PRODUCTS",
        )
    }

    vendor_primary = create_vendor(
        db,
        code=f"{tag}-VND-RAW",
        name=f"{tag} Materials Supply",
        lead_time_days=5,
        notes=f"[{tag}] benchmark raw material supplier",
    )
    vendor_finished = create_vendor(
        db,
        code=f"{tag}-VND-FG",
        name=f"{tag} Finished Goods Supply",
        lead_time_days=8,
        notes=f"[{tag}] benchmark finished goods supplier",
    )

    location = create_location(db, code=f"{tag}-MAIN", name=f"{tag} Benchmark Warehouse")

    wc_print = create_work_center(
        db, code=f"{tag}-PRINT", name=f"{tag} Print Cell", center_type="machine", hourly_rate=Decimal("45.00")
    )
    wc_qc = create_work_center(
        db, code=f"{tag}-QC", name=f"{tag} Quality", center_type="station", hourly_rate=Decimal("30.00")
    )
    wc_assembly = create_work_center(
        db, code=f"{tag}-ASSY", name=f"{tag} Assembly", center_type="station", hourly_rate=Decimal("32.00")
    )
    wc_shipping = create_work_center(
        db, code=f"{tag}-SHIP", name=f"{tag} Shipping", center_type="station", hourly_rate=Decimal("28.00")
    )

    printer_1 = create_resource(
        db,
        work_center=wc_print,
        code=f"{tag}-PRN-01",
        name="Benchmark Printer 01",
        machine_type="X1C",
        printer_class="enclosed",
    )
    printer_2 = create_resource(
        db,
        work_center=wc_print,
        code=f"{tag}-PRN-02",
        name="Benchmark Printer 02",
        machine_type="P1S",
        printer_class="enclosed",
    )
    create_resource(
        db,
        work_center=wc_print,
        code=f"{tag}-PRN-MAINT",
        name="Benchmark Printer Maintenance",
        status="maintenance",
        machine_type="A1",
        printer_class="open",
    )
    create_resource(db, work_center=wc_qc, code=f"{tag}-QC-01", name="Benchmark QC Station")
    create_resource(db, work_center=wc_assembly, code=f"{tag}-ASM-01", name="Benchmark Assembly Station")
    create_resource(db, work_center=wc_shipping, code=f"{tag}-SHP-01", name="Benchmark Shipping Station")

    materials = {
        "pla_black": create_product(
            db,
            sku=f"{tag}-MAT-PLA-BLK",
            name=f"{tag} PLA Black",
            description="Benchmark raw material for blocked and running orders.",
            item_type="supply",
            procurement_type="buy",
            category_id=categories["PLA"].id,
            unit="G",
            purchase_uom="KG",
            purchase_factor=Decimal("1000"),
            standard_cost=Decimal("22.50"),
            preferred_vendor_id=vendor_primary.id,
            reorder_point=Decimal("500"),
            safety_stock=Decimal("250"),
            stocking_policy="stocked",
            is_raw_material=True,
        ),
        "pla_natural": create_product(
            db,
            sku=f"{tag}-MAT-PLA-NAT",
            name=f"{tag} PLA Natural",
            description="Benchmark raw material for healthy supply.",
            item_type="supply",
            procurement_type="buy",
            category_id=categories["PLA"].id,
            unit="G",
            purchase_uom="KG",
            purchase_factor=Decimal("1000"),
            standard_cost=Decimal("21.00"),
            preferred_vendor_id=vendor_primary.id,
            reorder_point=Decimal("800"),
            safety_stock=Decimal("300"),
            stocking_policy="stocked",
            is_raw_material=True,
        ),
    }

    components = {
        "insert": create_product(
            db,
            sku=f"{tag}-COMP-INS-M3",
            name=f"{tag} M3 Insert",
            description="Benchmark component used in make items.",
            item_type="component",
            procurement_type="buy",
            category_id=categories["INSERTS"].id,
            unit="EA",
            standard_cost=Decimal("0.18"),
            preferred_vendor_id=vendor_primary.id,
            reorder_point=Decimal("40"),
            safety_stock=Decimal("20"),
            stocking_policy="stocked",
        ),
        "box": create_product(
            db,
            sku=f"{tag}-SUP-BOX-SM",
            name=f"{tag} Shipping Box",
            description="Benchmark packaging supply.",
            item_type="supply",
            procurement_type="buy",
            category_id=categories["BOXES"].id,
            unit="EA",
            standard_cost=Decimal("0.75"),
            preferred_vendor_id=vendor_primary.id,
            reorder_point=Decimal("25"),
            safety_stock=Decimal("10"),
            stocking_policy="stocked",
        ),
    }

    finished_goods = {
        "grid": create_product(
            db,
            sku=f"{tag}-FG-GRID",
            name=f"{tag} Grid Fixture",
            description="Benchmark make item that intentionally triggers shortages.",
            item_type="finished_good",
            procurement_type="make",
            category_id=categories["STANDARD_PRODUCTS"].id,
            unit="EA",
            standard_cost=Decimal("11.50"),
            selling_price=Decimal("34.99"),
            has_bom=True,
        ),
        "bracket": create_product(
            db,
            sku=f"{tag}-FG-BRACKET",
            name=f"{tag} Bracket Kit",
            description="Benchmark make item used for running work orders.",
            item_type="finished_good",
            procurement_type="make",
            category_id=categories["STANDARD_PRODUCTS"].id,
            unit="EA",
            standard_cost=Decimal("13.20"),
            selling_price=Decimal("39.50"),
            has_bom=True,
        ),
        "kit": create_product(
            db,
            sku=f"{tag}-FG-KIT",
            name=f"{tag} Ready Kit",
            description="Benchmark buy item used for quick order creation.",
            item_type="finished_good",
            procurement_type="buy",
            category_id=categories["STANDARD_PRODUCTS"].id,
            unit="EA",
            standard_cost=Decimal("14.00"),
            selling_price=Decimal("42.00"),
            preferred_vendor_id=vendor_finished.id,
            reorder_point=Decimal("8"),
            safety_stock=Decimal("3"),
            stocking_policy="stocked",
        ),
    }

    create_bom(
        db,
        product=finished_goods["grid"],
        code=f"BOM-{finished_goods['grid'].sku}",
        name=f"{finished_goods['grid'].name} BOM",
        lines=[
            (materials["pla_black"], Decimal("180"), "G", "production"),
            (components["insert"], Decimal("4"), "EA", "production"),
            (components["box"], Decimal("1"), "EA", "shipping"),
        ],
    )
    create_bom(
        db,
        product=finished_goods["bracket"],
        code=f"BOM-{finished_goods['bracket'].sku}",
        name=f"{finished_goods['bracket'].name} BOM",
        lines=[
            (materials["pla_natural"], Decimal("140"), "G", "production"),
            (components["insert"], Decimal("2"), "EA", "production"),
            (components["box"], Decimal("1"), "EA", "shipping"),
        ],
    )

    create_routing(
        db,
        product=finished_goods["grid"],
        code=f"RT-{finished_goods['grid'].sku}",
        name=f"{finished_goods['grid'].name} Routing",
        operations=[
            {
                "sequence": 10,
                "work_center_id": wc_print.id,
                "operation_code": "PRINT",
                "operation_name": "Print Grid Fixture",
                "setup_time_minutes": Decimal("8"),
                "run_time_minutes": Decimal("55"),
                "materials": [
                    {"component": materials["pla_black"], "quantity": Decimal("180"), "unit": "G"},
                ],
            },
            {
                "sequence": 20,
                "work_center_id": wc_assembly.id,
                "operation_code": "ASSEMBLE",
                "operation_name": "Insert Assembly",
                "setup_time_minutes": Decimal("2"),
                "run_time_minutes": Decimal("7"),
                "materials": [
                    {"component": components["insert"], "quantity": Decimal("4"), "unit": "EA"},
                ],
            },
            {
                "sequence": 30,
                "work_center_id": wc_shipping.id,
                "operation_code": "PACK",
                "operation_name": "Pack",
                "setup_time_minutes": Decimal("1"),
                "run_time_minutes": Decimal("3"),
                "materials": [
                    {"component": components["box"], "quantity": Decimal("1"), "unit": "EA"},
                ],
            },
        ],
    )
    create_routing(
        db,
        product=finished_goods["bracket"],
        code=f"RT-{finished_goods['bracket'].sku}",
        name=f"{finished_goods['bracket'].name} Routing",
        operations=[
            {
                "sequence": 10,
                "work_center_id": wc_print.id,
                "operation_code": "PRINT",
                "operation_name": "Print Bracket",
                "setup_time_minutes": Decimal("6"),
                "run_time_minutes": Decimal("42"),
                "materials": [
                    {"component": materials["pla_natural"], "quantity": Decimal("140"), "unit": "G"},
                ],
            },
            {
                "sequence": 20,
                "work_center_id": wc_qc.id,
                "operation_code": "QC",
                "operation_name": "Quality Check",
                "setup_time_minutes": Decimal("0"),
                "run_time_minutes": Decimal("4"),
            },
            {
                "sequence": 30,
                "work_center_id": wc_shipping.id,
                "operation_code": "PACK",
                "operation_name": "Pack",
                "setup_time_minutes": Decimal("1"),
                "run_time_minutes": Decimal("2"),
                "materials": [
                    {"component": components["box"], "quantity": Decimal("1"), "unit": "EA"},
                ],
            },
        ],
    )

    create_inventory_record(db, product=materials["pla_black"], location=location, on_hand=Decimal("300"))
    create_inventory_record(db, product=materials["pla_natural"], location=location, on_hand=Decimal("6000"))
    create_inventory_record(db, product=components["insert"], location=location, on_hand=Decimal("120"))
    create_inventory_record(db, product=components["box"], location=location, on_hand=Decimal("45"))
    create_inventory_record(db, product=finished_goods["grid"], location=location, on_hand=Decimal("0"))
    create_inventory_record(db, product=finished_goods["bracket"], location=location, on_hand=Decimal("3"))
    create_inventory_record(db, product=finished_goods["kit"], location=location, on_hand=Decimal("6"))

    customers = create_customer_users(db, count=config["customers"], tag=tag)

    open_pos = [
        create_purchase_order_seed(
            db,
            vendor=vendor_primary,
            items=[(materials["pla_black"], Decimal("5"), Decimal("22.50"))],
            notes=f"[{tag}] benchmark replenishment for black PLA",
            status="ordered",
            order_days_ago=1,
            expected_days_ahead=3,
        ),
        create_purchase_order_seed(
            db,
            vendor=vendor_finished,
            items=[(finished_goods["kit"], Decimal("20"), Decimal("14.00"))],
            notes=f"[{tag}] benchmark incoming finished goods",
            status="ordered",
            order_days_ago=2,
            expected_days_ahead=5,
        ),
    ]

    pending_order = create_sales_order_seed(
        db,
        slug="pending",
        customer=customers[0],
        lines=[OrderLineSpec(finished_goods["kit"], 3)],
        admin=admin,
        tag=tag,
    )

    confirmed_order = create_sales_order_seed(
        db,
        slug="confirmed",
        customer=customers[1],
        lines=[OrderLineSpec(finished_goods["kit"], 2)],
        admin=admin,
        tag=tag,
    )
    sales_order_service.update_sales_order_status(
        db,
        order_id=confirmed_order.id,
        new_status="confirmed",
        user_id=admin.id,
        user_email=admin.email,
    )
    confirmed_order.payment_status = "paid"
    confirmed_order.estimated_completion_date = now_utc() + timedelta(days=1)
    set_order_line_quantities(confirmed_order, allocations={finished_goods["kit"].id: Decimal("1")})

    blocked_order = create_sales_order_seed(
        db,
        slug="blocked",
        customer=customers[2],
        lines=[OrderLineSpec(finished_goods["grid"], 8)],
        admin=admin,
        tag=tag,
    )
    sales_order_service.update_sales_order_status(
        db,
        order_id=blocked_order.id,
        new_status="confirmed",
        user_id=admin.id,
        user_email=admin.email,
    )
    blocked_order.payment_status = "paid"
    blocked_order.estimated_completion_date = now_utc() - timedelta(days=1, hours=2)
    set_order_line_quantities(blocked_order)
    blocked_pos = get_production_orders_for_order(db, blocked_order)
    for production_order in blocked_pos:
        production_order.status = "released"
        production_order.due_date = date.today()
        production_order.notes = f"[{tag}] benchmark blocked work order"
        for operation in production_order.operations:
            operation.status = "pending"
            operation.resource_id = None

    partial_ready_order = create_sales_order_seed(
        db,
        slug="partial-ready",
        customer=customers[0],
        lines=[
            OrderLineSpec(finished_goods["kit"], 2),
            OrderLineSpec(finished_goods["bracket"], 3),
        ],
        admin=admin,
        tag=tag,
    )
    sales_order_service.update_sales_order_status(
        db,
        order_id=partial_ready_order.id,
        new_status="confirmed",
        user_id=admin.id,
        user_email=admin.email,
    )
    partial_ready_order.payment_status = "paid"
    partial_ready_order.estimated_completion_date = now_utc().replace(hour=17, minute=0, second=0, microsecond=0)
    set_order_line_quantities(
        partial_ready_order,
        allocations={
            finished_goods["kit"].id: Decimal("2"),
            finished_goods["bracket"].id: Decimal("0"),
        },
    )
    running_pos = get_production_orders_for_order(db, partial_ready_order)
    for production_order in running_pos:
        if production_order.product_id != finished_goods["bracket"].id:
            continue
        production_order.status = "in_progress"
        production_order.actual_start = now_utc() - timedelta(hours=6)
        production_order.due_date = date.today()
        production_order.notes = f"[{tag}] benchmark active work order"
        if production_order.operations:
            first_operation = production_order.operations[0]
            first_operation.status = "running"
            first_operation.resource_id = printer_1.id
            first_operation.actual_start = now_utc() - timedelta(hours=5)
            for operation in production_order.operations[1:]:
                operation.status = "pending"
                operation.resource_id = None

    ready_order = create_sales_order_seed(
        db,
        slug="ready",
        customer=customers[3 % len(customers)],
        lines=[OrderLineSpec(finished_goods["kit"], 1)],
        admin=admin,
        tag=tag,
    )
    ready_order.status = "ready_to_ship"
    ready_order.payment_status = "paid"
    ready_order.fulfillment_status = "ready"
    ready_order.confirmed_at = now_utc() - timedelta(days=1)
    ready_order.estimated_completion_date = now_utc()
    set_order_line_quantities(ready_order, allocations={finished_goods["kit"].id: Decimal("1")})

    shipped_order = create_sales_order_seed(
        db,
        slug="shipped",
        customer=customers[1],
        lines=[OrderLineSpec(finished_goods["kit"], 1)],
        admin=admin,
        tag=tag,
    )
    shipped_order.status = "shipped"
    shipped_order.payment_status = "paid"
    shipped_order.fulfillment_status = "shipped"
    shipped_order.confirmed_at = now_utc() - timedelta(days=2)
    shipped_order.shipped_at = now_utc() - timedelta(hours=3)
    set_order_line_quantities(
        shipped_order,
        allocations={finished_goods["kit"].id: Decimal("1")},
        shipments={finished_goods["kit"].id: Decimal("1")},
    )

    completed_order = create_sales_order_seed(
        db,
        slug="completed",
        customer=customers[2],
        lines=[OrderLineSpec(finished_goods["bracket"], 2)],
        admin=admin,
        tag=tag,
    )
    sales_order_service.update_sales_order_status(
        db,
        order_id=completed_order.id,
        new_status="confirmed",
        user_id=admin.id,
        user_email=admin.email,
    )
    completed_order.status = "completed"
    completed_order.payment_status = "paid"
    completed_order.fulfillment_status = "delivered"
    completed_order.confirmed_at = now_utc() - timedelta(days=3)
    completed_order.actual_completion_date = now_utc() - timedelta(hours=1)
    completed_order.shipped_at = now_utc() - timedelta(days=1)
    completed_order.delivered_at = now_utc()
    set_order_line_quantities(
        completed_order,
        allocations={finished_goods["bracket"].id: Decimal("2")},
        shipments={finished_goods["bracket"].id: Decimal("2")},
    )
    completed_pos = get_production_orders_for_order(db, completed_order)
    for production_order in completed_pos:
        production_order.status = "completed"
        production_order.quantity_completed = production_order.quantity_ordered
        production_order.completed_at = now_utc()
        for operation in production_order.operations:
            operation.status = "complete"
            operation.resource_id = printer_2.id if operation.sequence == 10 else None
            operation.actual_start = now_utc() - timedelta(hours=4)
            operation.actual_end = now_utc() - timedelta(hours=2)

    extra_orders: list[SalesOrder] = []
    extra_status_cycle = ("pending", "confirmed", "ready_to_ship", "shipped", "completed")
    extra_products = (finished_goods["kit"], finished_goods["grid"], finished_goods["bracket"])
    for index in range(config["extra_orders"]):
        customer = customers[index % len(customers)]
        product = extra_products[index % len(extra_products)]
        status_value = extra_status_cycle[index % len(extra_status_cycle)]
        order = create_sales_order_seed(
            db,
            slug=f"extra-{index + 1:03d}",
            customer=customer,
            lines=[OrderLineSpec(product, (index % 4) + 1)],
            admin=admin,
            tag=tag,
        )
        order.confirmed_at = now_utc() - timedelta(days=(index % 6) + 1)
        order.estimated_completion_date = now_utc() + timedelta(days=(index % 5) - 2)
        if status_value == "confirmed":
            order.status = "confirmed"
            order.payment_status = "paid"
        elif status_value == "ready_to_ship":
            order.status = "ready_to_ship"
            order.payment_status = "paid"
            order.fulfillment_status = "ready"
            set_order_line_quantities(order, allocations={product.id: Decimal(str(order.lines[0].quantity))})
        elif status_value == "shipped":
            order.status = "shipped"
            order.payment_status = "paid"
            order.shipped_at = now_utc() - timedelta(hours=(index % 12) + 1)
            set_order_line_quantities(
                order,
                allocations={product.id: Decimal(str(order.lines[0].quantity))},
                shipments={product.id: Decimal(str(order.lines[0].quantity))},
            )
        elif status_value == "completed":
            order.status = "completed"
            order.payment_status = "paid"
            order.actual_completion_date = now_utc() - timedelta(hours=(index % 8) + 1)
            set_order_line_quantities(
                order,
                allocations={product.id: Decimal(str(order.lines[0].quantity))},
                shipments={product.id: Decimal(str(order.lines[0].quantity))},
            )
        extra_orders.append(order)

    db.commit()

    overdue_invoice = invoice_service.create_invoice(db, ready_order.id)
    overdue_invoice.status = "sent"
    overdue_invoice.due_date = date.today() - timedelta(days=2)
    overdue_invoice.sent_at = now_utc() - timedelta(days=3)
    db.commit()

    paid_invoice = invoice_service.create_invoice(db, completed_order.id)
    invoice_service.record_payment(
        db,
        invoice_id=paid_invoice.id,
        amount=paid_invoice.total,
        method="card",
        reference=f"{tag}-paid",
    )

    all_orders = [
        pending_order,
        confirmed_order,
        blocked_order,
        partial_ready_order,
        ready_order,
        shipped_order,
        completed_order,
        *extra_orders,
    ]
    detail_targets = all_orders[: min(12, len(all_orders))]

    manifest = {
        "version": 1,
        "profile": profile,
        "tag": tag,
        "generated_at": now_utc().isoformat(),
        "admin": {
            "email": admin.email,
        },
        "customers": [
            {
                "id": customer.id,
                "email": customer.email,
                "name": customer.company_name or customer.full_name,
            }
            for customer in customers
        ],
        "products": {
            "make": [manifest_product(finished_goods["grid"]), manifest_product(finished_goods["bracket"])],
            "buy": [manifest_product(finished_goods["kit"])],
            "components": [manifest_product(components["insert"]), manifest_product(components["box"])],
            "materials": [manifest_product(materials["pla_black"]), manifest_product(materials["pla_natural"])],
        },
        "orders": {
            "representative": {
                "pending": manifest_order(pending_order),
                "confirmed": manifest_order(confirmed_order),
                "blocked": manifest_order(blocked_order),
                "partial_ready": manifest_order(partial_ready_order),
                "ready_to_ship": manifest_order(ready_order),
                "shipped": manifest_order(shipped_order),
                "completed": manifest_order(completed_order),
            },
            "detail_targets": [manifest_order(order) for order in detail_targets],
            "all_ids": [order.id for order in all_orders],
        },
        "purchase_orders": [po.po_number for po in open_pos],
        "resources": {
            "print": [printer_1.code, printer_2.code],
        },
    }
    return manifest


def write_manifest(manifest: dict, manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    assert_safe_target(args.allow_production)

    db = SessionLocal()
    try:
        admin = ensure_admin_user(db, args.admin_email, args.admin_password, args.tag)
        manifest = seed_dataset(db, profile=args.profile, tag=args.tag, admin=admin)
        manifest_path = Path(args.manifest).resolve()
        write_manifest(manifest, manifest_path)
        print(f"Wrote loadgen manifest to {manifest_path}")
        print(
            f"Seeded profile={args.profile} customers={len(manifest['customers'])} "
            f"orders={len(manifest['orders']['all_ids'])}"
        )
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
