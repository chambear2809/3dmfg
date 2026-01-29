"""
Pytest configuration and fixtures for the test suite.

Provides:
- Session-scoped seed data (location, user, work center)
- Database session fixture with rollback cleanup
- FastAPI TestClient with auth overrides
- Data factory fixtures for common domain objects
"""
import uuid
import pytest
import sys
from decimal import Decimal
from pathlib import Path

# Add the backend directory to the path so imports work correctly
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# =============================================================================
# Session-scoped seed data
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def seed_test_data():
    """Seed default records required by tests.

    Seeds:
    - InventoryLocation id=1 (tests create Inventory with location_id=1)
    - User id=1 (tests create Quotes with user_id=1)
    - WorkCenter id=1 (tests create ProductionOrderOperations with work_center_id)
    - GLAccounts for core accounting (inventory, COGS, revenue, AP, AR, WIP, scrap)
    """
    from app.db.session import SessionLocal
    from app.models.inventory import InventoryLocation
    from app.models.user import User
    from app.models.work_center import WorkCenter
    from app.models.accounting import GLAccount

    db = SessionLocal()
    try:
        # Seed default inventory location
        if not db.query(InventoryLocation).filter(InventoryLocation.id == 1).first():
            db.add(InventoryLocation(
                id=1, name="Default Warehouse", code="DEFAULT",
                type="warehouse", active=True,
            ))

        # Seed default test user
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(
                id=1, email="test@filaops.dev",
                password_hash="not-a-real-hash",
                first_name="Test", last_name="User",
                account_type="admin",
            ))

        # Seed default work center
        if not db.query(WorkCenter).filter(WorkCenter.id == 1).first():
            db.add(WorkCenter(
                id=1, code="TEST-WC", name="Test Work Center",
            ))

        # Seed core GL accounts (idempotent)
        gl_accounts = [
            ("1300", "Inventory Asset", "asset"),
            ("1310", "WIP Inventory", "asset"),
            ("1200", "Accounts Receivable", "asset"),
            ("2000", "Accounts Payable", "liability"),
            ("4000", "Sales Revenue", "revenue"),
            ("5000", "Cost of Goods Sold", "expense"),
            ("5100", "Material Cost", "expense"),
            ("5200", "Scrap Expense", "expense"),
            ("5500", "Inventory Adjustment", "expense"),
        ]
        for code, name, acct_type in gl_accounts:
            if not db.query(GLAccount).filter(GLAccount.account_code == code).first():
                db.add(GLAccount(account_code=code, name=name, account_type=acct_type))

        db.commit()
        yield
    finally:
        db.close()


# =============================================================================
# Database session fixture
# =============================================================================

@pytest.fixture
def db():
    """Create a database session that rolls back after each test."""
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# FastAPI TestClient with authentication
# =============================================================================

@pytest.fixture
def auth_token():
    """Generate a valid JWT access token for user_id=1 (seeded test admin)."""
    from app.core.security import create_access_token
    return create_access_token(user_id=1)


@pytest.fixture
def client(db, auth_token):
    """FastAPI TestClient with DB session override and auth.

    Usage:
        def test_list_items(client):
            response = client.get("/api/v1/items/")
            assert response.status_code == 200

        def test_unauthed(unauthed_client):
            response = unauthed_client.get("/api/v1/items/")
            assert response.status_code == 401
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db

    def _override_get_db():
        try:
            yield db
        finally:
            pass  # db fixture handles rollback

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        c.headers["Authorization"] = f"Bearer {auth_token}"
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(db):
    """FastAPI TestClient without authentication (for 401 tests)."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# =============================================================================
# Data factories — reusable fixtures for domain objects
# =============================================================================

def _uid():
    """Short unique suffix for test data."""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def make_product(db):
    """Factory fixture to create Product instances.

    Usage:
        product = make_product()  # defaults: finished_good, EA, average cost
        raw = make_product(item_type="supply", unit="G", purchase_uom="KG", purchase_factor=1000)
    """
    from app.models.product import Product

    created = []

    def _factory(
        sku=None,
        name=None,
        item_type="finished_good",
        unit="EA",
        purchase_uom="EA",
        purchase_factor=None,
        cost_method="average",
        standard_cost=None,
        average_cost=None,
        selling_price=None,
        is_raw_material=False,
        procurement_type="buy",
        **kwargs,
    ):
        uid = _uid()
        product = Product(
            sku=sku or f"TEST-{item_type[:3].upper()}-{uid}",
            name=name or f"Test {item_type} {uid}",
            item_type=item_type,
            unit=unit,
            purchase_uom=purchase_uom,
            purchase_factor=purchase_factor,
            cost_method=cost_method,
            standard_cost=standard_cost,
            average_cost=average_cost,
            selling_price=selling_price,
            is_raw_material=is_raw_material,
            procurement_type=procurement_type,
            **kwargs,
        )
        db.add(product)
        db.flush()
        created.append(product)
        return product

    yield _factory


@pytest.fixture
def make_vendor(db):
    """Factory fixture to create Vendor instances."""
    from app.models.vendor import Vendor

    def _factory(name=None, code=None, **kwargs):
        uid = _uid()
        vendor = Vendor(
            code=code or f"V-{uid}",
            name=name or f"Test Vendor {uid}",
            is_active=True,
            **kwargs,
        )
        db.add(vendor)
        db.flush()
        return vendor

    yield _factory


@pytest.fixture
def make_customer(db):
    """Factory fixture to create Customer instances."""
    from app.models.customer import Customer

    def _factory(company_name=None, email=None, **kwargs):
        uid = _uid()
        customer = Customer(
            company_name=company_name or f"Test Co {uid}",
            email=email or f"test-{uid}@example.com",
            status="active",
            **kwargs,
        )
        db.add(customer)
        db.flush()
        return customer

    yield _factory


@pytest.fixture
def make_sales_order(db):
    """Factory fixture to create SalesOrder instances.

    Usage:
        so = make_sales_order(product_id=product.id, quantity=10, unit_price=Decimal("5.00"))
    """
    from app.models.sales_order import SalesOrder

    _counter = [0]

    def _factory(
        product_id=None,
        quantity=1,
        unit_price=Decimal("10.00"),
        status="draft",
        material_type="PLA",
        **kwargs,
    ):
        uid = _uid()
        _counter[0] += 1
        total = unit_price * quantity
        so = SalesOrder(
            order_number=kwargs.pop("order_number", f"SO-TEST-{uid}"),
            user_id=kwargs.pop("user_id", 1),
            product_id=product_id,
            product_name=kwargs.pop("product_name", f"Test Product {uid}"),
            quantity=quantity,
            material_type=material_type,
            unit_price=unit_price,
            total_price=total,
            grand_total=total,
            status=status,
            **kwargs,
        )
        db.add(so)
        db.flush()
        return so

    yield _factory


@pytest.fixture
def make_purchase_order(db):
    """Factory fixture to create PurchaseOrder instances."""
    from app.models.purchase_order import PurchaseOrder

    def _factory(vendor_id=None, status="draft", **kwargs):
        uid = _uid()
        po = PurchaseOrder(
            po_number=kwargs.pop("po_number", f"PO-TEST-{uid}"),
            vendor_id=vendor_id,
            status=status,
            created_by=kwargs.pop("created_by", 1),
            **kwargs,
        )
        db.add(po)
        db.flush()
        return po

    yield _factory


@pytest.fixture
def make_bom(db):
    """Factory fixture to create BOM with lines.

    Usage:
        bom = make_bom(product_id=fg.id, lines=[
            {"component_id": raw.id, "quantity": Decimal("100"), "unit": "G"},
        ])
    """
    from app.models.bom import BOM, BOMLine

    def _factory(product_id, lines=None, **kwargs):
        uid = _uid()
        bom = BOM(
            product_id=product_id,
            name=kwargs.pop("name", f"BOM-{uid}"),
            active=True,
            **kwargs,
        )
        db.add(bom)
        db.flush()

        if lines:
            for i, line_data in enumerate(lines):
                line = BOMLine(
                    bom_id=bom.id,
                    component_id=line_data["component_id"],
                    quantity=line_data.get("quantity", Decimal("1")),
                    unit=line_data.get("unit", "EA"),
                    sequence=line_data.get("sequence", (i + 1) * 10),
                )
                db.add(line)
            db.flush()

        return bom

    yield _factory


# =============================================================================
# Convenience fixtures for common test scenarios
# =============================================================================

@pytest.fixture
def raw_material(make_product):
    """A filament raw material: unit=G, purchase_uom=KG, cost_method=average."""
    return make_product(
        item_type="supply",
        unit="G",
        purchase_uom="KG",
        purchase_factor=Decimal("1000"),
        cost_method="average",
        average_cost=Decimal("0.02"),
        is_raw_material=True,
        name="PLA Filament (Test)",
    )


@pytest.fixture
def finished_good(make_product):
    """A finished good product with standard costing."""
    return make_product(
        item_type="finished_good",
        unit="EA",
        cost_method="standard",
        standard_cost=Decimal("5.00"),
        selling_price=Decimal("15.00"),
        procurement_type="make",
        name="Test Widget (FG)",
    )
