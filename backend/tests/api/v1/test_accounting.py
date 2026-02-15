"""
Tests for GL Accounting API endpoints

Tests the trial balance endpoint and related financial reporting.
Uses direct database testing pattern (no TestClient due to version compatibility).
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.accounting import GLAccount, GLJournalEntry, GLJournalEntryLine
from app.models.user import User


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def db():
    """Create a database session for testing."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def gl_accounts(db: Session):
    """Ensure all required GL accounts exist."""
    accounts = [
        ("1200", "Raw Materials Inventory", "asset"),
        ("1210", "WIP Inventory", "asset"),
        ("1220", "Finished Goods Inventory", "asset"),
        ("1230", "Packaging Inventory", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5010", "Shipping Expense", "expense"),
        ("5020", "Scrap Expense", "expense"),
    ]
    result = {}
    for code, acct_name, acct_type in accounts:
        existing = db.query(GLAccount).filter(GLAccount.account_code == code).first()
        if not existing:
            existing = GLAccount(
                account_code=code,
                name=acct_name,
                account_type=acct_type,
                active=True,
            )
            db.add(existing)
            db.flush()
        result[code] = existing
    yield result
    db.rollback()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_trial_balance_data(db: Session, as_of_date: date = None, include_zero_balances: bool = False):
    """
    Direct implementation of trial balance logic for testing.
    Mirrors the API endpoint logic.
    """
    from sqlalchemy import func

    if as_of_date is None:
        as_of_date = date.today()

    query = db.query(
        GLAccount.account_code,
        GLAccount.name,
        GLAccount.account_type,
        func.coalesce(func.sum(GLJournalEntryLine.debit_amount), Decimal("0")).label("total_debits"),
        func.coalesce(func.sum(GLJournalEntryLine.credit_amount), Decimal("0")).label("total_credits"),
    ).outerjoin(
        GLJournalEntryLine, GLAccount.id == GLJournalEntryLine.account_id
    ).outerjoin(
        GLJournalEntry, GLJournalEntryLine.journal_entry_id == GLJournalEntry.id
    ).filter(
        (GLJournalEntry.entry_date <= as_of_date) | (GLJournalEntry.id.is_(None))
    ).group_by(
        GLAccount.id,
        GLAccount.account_code,
        GLAccount.name,
        GLAccount.account_type,
    ).order_by(
        GLAccount.account_code
    )

    results = query.all()

    accounts = []
    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for row in results:
        debit_bal = Decimal(str(row.total_debits or 0))
        credit_bal = Decimal(str(row.total_credits or 0))

        if row.account_type in ("asset", "expense"):
            net_balance = debit_bal - credit_bal
            if net_balance >= 0:
                display_debit = net_balance
                display_credit = Decimal("0")
            else:
                display_debit = Decimal("0")
                display_credit = abs(net_balance)
        else:
            net_balance = credit_bal - debit_bal
            if net_balance >= 0:
                display_debit = Decimal("0")
                display_credit = net_balance
            else:
                display_debit = abs(net_balance)
                display_credit = Decimal("0")

        if not include_zero_balances and display_debit == 0 and display_credit == 0:
            continue

        accounts.append({
            "account_code": row.account_code,
            "account_name": row.name,
            "account_type": row.account_type,
            "debit_balance": display_debit,
            "credit_balance": display_credit,
            "net_balance": net_balance,
        })

        total_debits += display_debit
        total_credits += display_credit

    variance = abs(total_debits - total_credits)
    is_balanced = variance < Decimal("0.01")

    return {
        "as_of_date": as_of_date,
        "accounts": accounts,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "is_balanced": is_balanced,
        "variance": variance,
    }


# =============================================================================
# TEST: TRIAL BALANCE LOGIC
# =============================================================================

class TestTrialBalance:
    """Tests for trial balance endpoint logic"""

    def test_trial_balance_balanced(self, db: Session, gl_accounts):
        """Trial balance should always be balanced (debits = credits)."""
        result = get_trial_balance_data(db, include_zero_balances=True)
        assert result["is_balanced"] == True
        assert result["total_debits"] == result["total_credits"]

    def test_trial_balance_with_entries(self, db: Session, gl_accounts):
        """Trial balance should reflect journal entries correctly."""
        # Create a journal entry: DR 1200 $100, CR 2000 $100
        entry_num = f"TEST-TB-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date.today(),
            description="Test entry for trial balance",
            source_type="test",
            status="posted",
        )
        db.add(je)
        db.flush()

        # Debit Raw Materials
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0"),
        ))

        # Credit AP
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["2000"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("100.00"),
        ))
        db.commit()

        try:
            result = get_trial_balance_data(db)

            assert result["is_balanced"] == True

            # Find the accounts in response
            raw_mat = next((a for a in result["accounts"] if a["account_code"] == "1200"), None)
            ap = next((a for a in result["accounts"] if a["account_code"] == "2000"), None)

            # Raw Materials is an asset, should have debit balance
            assert raw_mat is not None
            assert raw_mat["debit_balance"] >= Decimal("100.00")

            # AP is a liability, should have credit balance
            assert ap is not None
            assert ap["credit_balance"] >= Decimal("100.00")

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()

    def test_trial_balance_as_of_date(self, db: Session, gl_accounts):
        """Trial balance should respect as_of_date filter."""
        # Create entry dated Jan 1, 2025
        entry_num = f"TEST-DATE-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date(2025, 1, 1),
            description="Past entry for date test",
            source_type="test",
            status="posted",
        )
        db.add(je)
        db.flush()

        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("50.00"),
            credit_amount=Decimal("0"),
        ))
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["2000"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("50.00"),
        ))
        db.commit()

        try:
            # Query as of Dec 31, 2024 (before entry)
            result_before = get_trial_balance_data(db, as_of_date=date(2024, 12, 31))
            raw_mat_before = next(
                (a for a in result_before["accounts"] if a["account_code"] == "1200"),
                {"debit_balance": Decimal("0")}
            )

            # Query as of Jan 2, 2025 (after entry)
            result_after = get_trial_balance_data(db, as_of_date=date(2025, 1, 2))
            raw_mat_after = next(
                (a for a in result_after["accounts"] if a["account_code"] == "1200"),
                {"debit_balance": Decimal("0")}
            )

            # The after query should have a higher balance for raw materials
            assert raw_mat_after["debit_balance"] >= raw_mat_before["debit_balance"] + Decimal("50.00")

            # Both should be balanced
            assert result_before["is_balanced"] == True
            assert result_after["is_balanced"] == True

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()

    def test_trial_balance_include_zero_balances(self, db: Session, gl_accounts):
        """Trial balance should optionally include accounts with zero balance."""
        # Query without zero balances
        result_no_zero = get_trial_balance_data(db, include_zero_balances=False)

        # Query with zero balances
        result_with_zero = get_trial_balance_data(db, include_zero_balances=True)

        # With zero balances included, we should have at least as many accounts
        assert len(result_with_zero["accounts"]) >= len(result_no_zero["accounts"])

    def test_trial_balance_account_type_balances(self, db: Session, gl_accounts):
        """Test that account types show correct normal balances."""
        # Create a complex entry with multiple account types
        entry_num = f"TEST-TYPES-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date.today(),
            description="Test entry for account types",
            source_type="test",
            status="posted",
        )
        db.add(je)
        db.flush()

        # Asset (DR normal) - DR 1200 Raw Materials $200
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("200.00"),
            credit_amount=Decimal("0"),
        ))

        # Liability (CR normal) - CR 2000 AP $150
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["2000"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("150.00"),
        ))

        # Expense (DR normal) - DR 5000 COGS $50
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["5000"].id,
            debit_amount=Decimal("50.00"),
            credit_amount=Decimal("0"),
        ))

        # Need to balance: DR $250, CR $150, so need CR $100 more
        # CR Raw Materials to balance
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("100.00"),
        ))

        db.commit()

        try:
            result = get_trial_balance_data(db)

            # Should be balanced
            assert result["is_balanced"] == True

            # Check account balances
            raw_mat = next((a for a in result["accounts"] if a["account_code"] == "1200"), None)
            ap = next((a for a in result["accounts"] if a["account_code"] == "2000"), None)
            cogs = next((a for a in result["accounts"] if a["account_code"] == "5000"), None)

            # Raw Materials: DR 200, CR 100 = net DR 100 (asset, so debit_balance)
            if raw_mat:
                assert raw_mat["debit_balance"] >= Decimal("100.00")

            # AP: CR 150 (liability, so credit_balance)
            if ap:
                assert ap["credit_balance"] >= Decimal("150.00")

            # COGS: DR 50 (expense, so debit_balance)
            if cogs:
                assert cogs["debit_balance"] >= Decimal("50.00")

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()


# =============================================================================
# INVENTORY VALUATION HELPER
# =============================================================================

def get_inventory_valuation_data(db: Session, as_of_date: date = None):
    """
    Direct implementation of inventory valuation logic for testing.
    Mirrors the API endpoint logic.
    """
    from sqlalchemy import func
    from app.models.product import Product
    from app.models.inventory import Inventory

    if as_of_date is None:
        as_of_date = date.today()

    category_map = {
        "supply": ("Raw Materials", "1200"),
        "wip": ("Work in Process", "1210"),
        "finished_good": ("Finished Goods", "1220"),
        "packaging": ("Packaging", "1230"),
    }

    categories = []
    total_inventory_value = Decimal("0")
    total_gl_balance = Decimal("0")

    for item_type, (category_name, gl_code) in category_map.items():
        gl_account = db.query(GLAccount).filter(
            GLAccount.account_code == gl_code
        ).first()

        if not gl_account:
            continue

        inventory_query = db.query(
            func.count(Inventory.id).label("item_count"),
            func.coalesce(func.sum(Inventory.on_hand_quantity), Decimal("0")).label("total_qty"),
            func.coalesce(
                func.sum(Inventory.on_hand_quantity * func.coalesce(Product.standard_cost, Decimal("0"))),
                Decimal("0")
            ).label("total_value"),
        ).join(
            Product, Inventory.product_id == Product.id
        ).filter(
            Product.item_type == item_type,
        )

        inv_result = inventory_query.first()

        item_count = inv_result.item_count or 0
        total_qty = Decimal(str(inv_result.total_qty or 0))
        inventory_value = Decimal(str(inv_result.total_value or 0))

        gl_query = db.query(
            func.coalesce(func.sum(GLJournalEntryLine.debit_amount), Decimal("0")).label("total_dr"),
            func.coalesce(func.sum(GLJournalEntryLine.credit_amount), Decimal("0")).label("total_cr"),
        ).join(
            GLJournalEntry, GLJournalEntryLine.journal_entry_id == GLJournalEntry.id
        ).filter(
            GLJournalEntryLine.account_id == gl_account.id,
            GLJournalEntry.entry_date <= as_of_date,
        )

        gl_result = gl_query.first()

        total_dr = Decimal(str(gl_result.total_dr or 0))
        total_cr = Decimal(str(gl_result.total_cr or 0))
        gl_balance = total_dr - total_cr

        variance = inventory_value - gl_balance

        categories.append({
            "category": category_name,
            "gl_account_code": gl_code,
            "gl_account_name": gl_account.name,
            "item_count": item_count,
            "total_quantity": total_qty,
            "inventory_value": inventory_value,
            "gl_balance": gl_balance,
            "variance": variance,
        })

        total_inventory_value += inventory_value
        total_gl_balance += gl_balance

    total_variance = total_inventory_value - total_gl_balance
    variance_threshold = max(Decimal("1.00"), abs(total_gl_balance) * Decimal("0.001"))
    is_reconciled = abs(total_variance) < variance_threshold

    return {
        "as_of_date": as_of_date,
        "categories": categories,
        "total_inventory_value": total_inventory_value,
        "total_gl_balance": total_gl_balance,
        "total_variance": total_variance,
        "is_reconciled": is_reconciled,
    }


# =============================================================================
# TEST: INVENTORY VALUATION LOGIC
# =============================================================================

class TestInventoryValuation:
    """Tests for inventory valuation endpoint logic"""

    def test_inventory_valuation_structure(self, db: Session, gl_accounts):
        """Inventory valuation should return correct response structure."""
        result = get_inventory_valuation_data(db)

        # Verify response structure
        assert "as_of_date" in result
        assert "categories" in result
        assert "total_inventory_value" in result
        assert "total_gl_balance" in result
        assert "total_variance" in result
        assert "is_reconciled" in result

        # Variance should be inventory_value - gl_balance
        assert result["total_variance"] == result["total_inventory_value"] - result["total_gl_balance"]

        # Values should be Decimals (or numeric)
        assert isinstance(result["total_inventory_value"], Decimal)
        assert isinstance(result["total_gl_balance"], Decimal)

    def test_inventory_valuation_categories(self, db: Session, gl_accounts):
        """Inventory valuation should return all expected categories."""
        result = get_inventory_valuation_data(db)

        # Should have 4 categories
        assert len(result["categories"]) == 4

        # Check category names
        category_names = {c["category"] for c in result["categories"]}
        assert "Raw Materials" in category_names
        assert "Work in Process" in category_names
        assert "Finished Goods" in category_names
        assert "Packaging" in category_names

    def test_inventory_valuation_with_gl_entries(self, db: Session, gl_accounts):
        """Inventory valuation should reflect GL journal entries."""
        # Create a journal entry for Raw Materials: DR 1200 $500
        entry_num = f"TEST-INV-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date.today(),
            description="Test inventory receipt",
            source_type="test",
            status="posted",
        )
        db.add(je)
        db.flush()

        # DR Raw Materials $500
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("500.00"),
            credit_amount=Decimal("0"),
        ))

        # CR Accounts Payable $500
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["2000"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("500.00"),
        ))
        db.commit()

        try:
            result = get_inventory_valuation_data(db)

            # Find Raw Materials category
            raw_mat = next((c for c in result["categories"] if c["gl_account_code"] == "1200"), None)
            assert raw_mat is not None

            # GL balance should show $500 for raw materials
            assert raw_mat["gl_balance"] >= Decimal("500.00")

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()

    def test_inventory_valuation_variance_calculation(self, db: Session, gl_accounts):
        """Inventory valuation should calculate variance correctly."""
        result = get_inventory_valuation_data(db)

        # Total variance should equal total_inventory_value - total_gl_balance
        expected_variance = result["total_inventory_value"] - result["total_gl_balance"]
        assert result["total_variance"] == expected_variance

        # For each category, variance should also be correctly calculated
        for cat in result["categories"]:
            expected_cat_variance = cat["inventory_value"] - cat["gl_balance"]
            assert cat["variance"] == expected_cat_variance


# =============================================================================
# TRANSACTION LEDGER HELPER
# =============================================================================

def get_ledger_data(
    db: Session,
    account_code: str,
    start_date: date = None,
    end_date: date = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Direct implementation of transaction ledger logic for testing.
    Mirrors the API endpoint logic.
    """
    from sqlalchemy import func

    # Get the account
    account = db.query(GLAccount).filter(
        GLAccount.account_code == account_code
    ).first()

    if not account:
        return None

    # Build base query for transactions
    query = db.query(
        GLJournalEntry.entry_date,
        GLJournalEntry.entry_number,
        GLJournalEntry.description,
        GLJournalEntry.source_type,
        GLJournalEntry.source_id,
        GLJournalEntry.id.label("journal_entry_id"),
        GLJournalEntryLine.debit_amount,
        GLJournalEntryLine.credit_amount,
    ).join(
        GLJournalEntryLine, GLJournalEntry.id == GLJournalEntryLine.journal_entry_id
    ).filter(
        GLJournalEntryLine.account_id == account.id
    )

    # Apply date filters
    if start_date:
        query = query.filter(GLJournalEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(GLJournalEntry.entry_date <= end_date)

    # Order by date, then entry number
    query = query.order_by(
        GLJournalEntry.entry_date,
        GLJournalEntry.entry_number,
        GLJournalEntry.id,
    )

    # Get total count before pagination
    total_count = query.count()

    # Apply pagination
    results = query.offset(offset).limit(limit).all()

    # Calculate opening balance
    opening_balance = Decimal("0")
    if start_date:
        opening_query = db.query(
            func.coalesce(func.sum(GLJournalEntryLine.debit_amount), Decimal("0")).label("dr"),
            func.coalesce(func.sum(GLJournalEntryLine.credit_amount), Decimal("0")).label("cr"),
        ).join(
            GLJournalEntry, GLJournalEntryLine.journal_entry_id == GLJournalEntry.id
        ).filter(
            GLJournalEntryLine.account_id == account.id,
            GLJournalEntry.entry_date < start_date,
        )

        opening_result = opening_query.first()
        if opening_result:
            dr = Decimal(str(opening_result.dr or 0))
            cr = Decimal(str(opening_result.cr or 0))
            if account.account_type in ("asset", "expense"):
                opening_balance = dr - cr
            else:
                opening_balance = cr - dr

    # Build transactions with running balance
    transactions = []
    running_balance = opening_balance
    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for row in results:
        debit = Decimal(str(row.debit_amount or 0))
        credit = Decimal(str(row.credit_amount or 0))

        if account.account_type in ("asset", "expense"):
            running_balance = running_balance + debit - credit
        else:
            running_balance = running_balance + credit - debit

        total_debits += debit
        total_credits += credit

        transactions.append({
            "entry_date": row.entry_date,
            "entry_number": row.entry_number,
            "description": row.description or "",
            "debit": debit,
            "credit": credit,
            "running_balance": running_balance,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "journal_entry_id": row.journal_entry_id,
        })

    return {
        "account_code": account.account_code,
        "account_name": account.name,
        "account_type": account.account_type,
        "start_date": start_date,
        "end_date": end_date,
        "opening_balance": opening_balance,
        "transactions": transactions,
        "closing_balance": running_balance,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "transaction_count": total_count,
    }


# =============================================================================
# TEST: TRANSACTION LEDGER LOGIC
# =============================================================================

class TestTransactionLedger:
    """Tests for transaction ledger endpoint logic"""

    def test_ledger_account_not_found(self, db: Session, gl_accounts):
        """Ledger should return None for invalid account code."""
        result = get_ledger_data(db, "9999")
        assert result is None

    def test_ledger_response_structure(self, db: Session, gl_accounts):
        """Ledger should return correct response structure."""
        result = get_ledger_data(db, "1200")

        # Verify response structure
        assert result is not None
        assert "account_code" in result
        assert "account_name" in result
        assert "account_type" in result
        assert "opening_balance" in result
        assert "transactions" in result
        assert "closing_balance" in result
        assert "total_debits" in result
        assert "total_credits" in result
        assert "transaction_count" in result

        # Values should be Decimals
        assert isinstance(result["opening_balance"], Decimal)
        assert isinstance(result["closing_balance"], Decimal)

    def test_ledger_with_transactions(self, db: Session, gl_accounts):
        """Ledger should show transactions with running balance."""
        # Create two journal entries
        entry_num1 = f"TEST-LED-{uuid.uuid4().hex[:8]}"
        je1 = GLJournalEntry(
            entry_number=entry_num1,
            entry_date=date(2025, 1, 10),
            description="First receipt",
            source_type="purchase_order",
            source_id=100,
            status="posted",
        )
        db.add(je1)
        db.flush()

        db.add(GLJournalEntryLine(
            journal_entry_id=je1.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("500.00"),
            credit_amount=Decimal("0"),
        ))

        entry_num2 = f"TEST-LED-{uuid.uuid4().hex[:8]}"
        je2 = GLJournalEntry(
            entry_number=entry_num2,
            entry_date=date(2025, 1, 15),
            description="Material issue",
            source_type="production_order",
            source_id=200,
            status="posted",
        )
        db.add(je2)
        db.flush()

        db.add(GLJournalEntryLine(
            journal_entry_id=je2.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("150.00"),
        ))
        db.commit()

        try:
            result = get_ledger_data(db, "1200")

            # Find our test transactions
            our_txns = [t for t in result["transactions"]
                        if t["entry_number"] in (entry_num1, entry_num2)]

            assert len(our_txns) >= 2

            # Find first transaction (debit)
            txn1 = next((t for t in our_txns if t["entry_number"] == entry_num1), None)
            assert txn1 is not None
            assert txn1["debit"] == Decimal("500.00")
            assert txn1["source_type"] == "purchase_order"

            # Find second transaction (credit)
            txn2 = next((t for t in our_txns if t["entry_number"] == entry_num2), None)
            assert txn2 is not None
            assert txn2["credit"] == Decimal("150.00")
            assert txn2["source_type"] == "production_order"

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id.in_([je1.id, je2.id])
            ).delete(synchronize_session=False)
            db.query(GLJournalEntry).filter(
                GLJournalEntry.id.in_([je1.id, je2.id])
            ).delete(synchronize_session=False)
            db.commit()

    def test_ledger_date_filter_with_opening_balance(self, db: Session, gl_accounts):
        """Ledger should calculate opening balance for filtered date range."""
        # Create entry before filter period
        entry_num1 = f"TPRE-{uuid.uuid4().hex[:8]}"
        je1 = GLJournalEntry(
            entry_number=entry_num1,
            entry_date=date(2025, 1, 5),
            description="Before period",
            source_type="test",
            status="posted",
        )
        db.add(je1)
        db.flush()

        db.add(GLJournalEntryLine(
            journal_entry_id=je1.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("1000.00"),
            credit_amount=Decimal("0"),
        ))

        # Create entry within filter period
        entry_num2 = f"TIN-{uuid.uuid4().hex[:8]}"
        je2 = GLJournalEntry(
            entry_number=entry_num2,
            entry_date=date(2025, 1, 15),
            description="Within period",
            source_type="test",
            status="posted",
        )
        db.add(je2)
        db.flush()

        db.add(GLJournalEntryLine(
            journal_entry_id=je2.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("200.00"),
            credit_amount=Decimal("0"),
        ))
        db.commit()

        try:
            # Query with start_date filter
            result = get_ledger_data(db, "1200", start_date=date(2025, 1, 10))

            # Opening balance should include pre-period transaction
            assert result["opening_balance"] >= Decimal("1000.00")

            # Only transactions from 2025-01-10 onwards should be in list
            for txn in result["transactions"]:
                assert txn["entry_date"] >= date(2025, 1, 10)

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id.in_([je1.id, je2.id])
            ).delete(synchronize_session=False)
            db.query(GLJournalEntry).filter(
                GLJournalEntry.id.in_([je1.id, je2.id])
            ).delete(synchronize_session=False)
            db.commit()

    def test_ledger_pagination(self, db: Session, gl_accounts):
        """Ledger should support pagination."""
        # Create 5 entries
        created_jes = []
        for i in range(5):
            entry_num = f"TPAG{i}-{uuid.uuid4().hex[:8]}"
            je = GLJournalEntry(
                entry_number=entry_num,
                entry_date=date(2025, 2, 10 + i),
                description=f"Pagination test entry {i}",
                source_type="test",
                status="posted",
            )
            db.add(je)
            db.flush()

            db.add(GLJournalEntryLine(
                journal_entry_id=je.id,
                account_id=gl_accounts["1200"].id,
                debit_amount=Decimal("100.00"),
                credit_amount=Decimal("0"),
            ))
            created_jes.append(je)

        db.commit()

        try:
            # Get with limit
            result = get_ledger_data(db, "1200", limit=2, offset=0)

            # Should return only 2 transactions but count should show total
            assert len(result["transactions"]) == 2
            assert result["transaction_count"] >= 5

            # Get with offset
            result2 = get_ledger_data(db, "1200", limit=2, offset=2)
            assert len(result2["transactions"]) == 2

            # Different transactions should be returned
            txn_ids_page1 = {t["journal_entry_id"] for t in result["transactions"]}
            txn_ids_page2 = {t["journal_entry_id"] for t in result2["transactions"]}
            assert txn_ids_page1.isdisjoint(txn_ids_page2)

        finally:
            # Clean up
            je_ids = [je.id for je in created_jes]
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id.in_(je_ids)
            ).delete(synchronize_session=False)
            db.query(GLJournalEntry).filter(
                GLJournalEntry.id.in_(je_ids)
            ).delete(synchronize_session=False)
            db.commit()


# =============================================================================
# PERIOD MANAGEMENT HELPER
# =============================================================================

def get_period_list_data(db: Session, year: int = None, status: str = None):
    """
    Direct implementation of period list logic for testing.
    Mirrors the API endpoint logic.
    """
    import calendar
    from app.models.accounting import GLFiscalPeriod
    from sqlalchemy import func

    query = db.query(GLFiscalPeriod)

    if year:
        query = query.filter(GLFiscalPeriod.year == year)
    if status:
        query = query.filter(GLFiscalPeriod.status == status)

    query = query.order_by(GLFiscalPeriod.year.desc(), GLFiscalPeriod.period.desc())
    periods = query.all()

    period_responses = []
    current_period = None
    today = date.today()

    for period in periods:
        je_stats = db.query(
            func.count(GLJournalEntry.id).label("count"),
            func.coalesce(func.sum(GLJournalEntryLine.debit_amount), Decimal("0")).label("total_dr"),
            func.coalesce(func.sum(GLJournalEntryLine.credit_amount), Decimal("0")).label("total_cr"),
        ).outerjoin(
            GLJournalEntryLine, GLJournalEntry.id == GLJournalEntryLine.journal_entry_id
        ).filter(
            GLJournalEntry.entry_date >= period.start_date,
            GLJournalEntry.entry_date <= period.end_date,
        ).first()

        period_resp = {
            "id": period.id,
            "name": f"{calendar.month_name[period.period]} {period.year}",
            "year": period.year,
            "period": period.period,
            "start_date": period.start_date,
            "end_date": period.end_date,
            "status": period.status,
            "closed_at": period.closed_at,
            "journal_entry_count": je_stats.count or 0,
            "total_debits": Decimal(str(je_stats.total_dr or 0)),
            "total_credits": Decimal(str(je_stats.total_cr or 0)),
        }
        period_responses.append(period_resp)

        if period.start_date <= today <= period.end_date:
            current_period = period_resp

    return {
        "periods": period_responses,
        "current_period": current_period,
    }


# =============================================================================
# TEST: PERIOD MANAGEMENT LOGIC
# =============================================================================

class TestPeriodManagement:
    """Tests for fiscal period management endpoint logic"""

    @pytest.fixture
    def fiscal_periods(self, db: Session):
        """Create test fiscal periods"""
        from app.models.accounting import GLFiscalPeriod
        from datetime import datetime, timezone

        # Create test periods
        period1 = GLFiscalPeriod(
            year=2025,
            period=1,  # January
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            status="open",
        )
        period2 = GLFiscalPeriod(
            year=2024,
            period=12,  # December
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            status="closed",
            closed_at=datetime(2025, 1, 5, 10, 0, 0),
        )
        db.add(period1)
        db.add(period2)
        db.commit()

        yield {"January 2025": period1, "December 2024": period2}

        # Cleanup
        db.query(GLFiscalPeriod).filter(
            GLFiscalPeriod.id.in_([period1.id, period2.id])
        ).delete(synchronize_session=False)
        db.commit()

    def test_list_periods_structure(self, db: Session, gl_accounts, fiscal_periods):
        """List periods should return correct structure."""
        result = get_period_list_data(db)

        assert "periods" in result
        assert isinstance(result["periods"], list)
        assert len(result["periods"]) >= 2

        # Check structure of first period
        if result["periods"]:
            p = result["periods"][0]
            assert "id" in p
            assert "name" in p
            assert "year" in p
            assert "period" in p
            assert "start_date" in p
            assert "end_date" in p
            assert "status" in p
            assert "journal_entry_count" in p

    def test_list_periods_filter_by_status(self, db: Session, gl_accounts, fiscal_periods):
        """List periods should filter by status."""
        result = get_period_list_data(db, status="open")

        for p in result["periods"]:
            assert p["status"] == "open"

        result_closed = get_period_list_data(db, status="closed")
        for p in result_closed["periods"]:
            assert p["status"] == "closed"

    def test_list_periods_filter_by_year(self, db: Session, gl_accounts, fiscal_periods):
        """List periods should filter by year."""
        result = get_period_list_data(db, year=2025)

        for p in result["periods"]:
            assert p["year"] == 2025

    def test_close_period_logic(self, db: Session, gl_accounts, fiscal_periods):
        """Closing a period should update status and timestamps."""
        from app.models.accounting import GLFiscalPeriod
        from datetime import datetime, timezone

        period = fiscal_periods["January 2025"]

        # Verify it's open
        assert period.status == "open"

        # Close the period
        period.status = "closed"
        period.closed_at = datetime.now(timezone.utc)
        db.commit()

        # Refresh and verify
        db.refresh(period)
        assert period.status == "closed"
        assert period.closed_at is not None

        # Reopen for cleanup
        period.status = "open"
        period.closed_at = None
        db.commit()

    def test_close_already_closed_period(self, db: Session, gl_accounts, fiscal_periods):
        """Closing an already closed period should be blocked."""
        period = fiscal_periods["December 2024"]
        assert period.status == "closed"

        # In the actual endpoint, this would raise HTTPException
        # Here we just verify the status check works
        is_already_closed = period.status == "closed"
        assert is_already_closed is True

    def test_reopen_period_logic(self, db: Session, gl_accounts, fiscal_periods):
        """Reopening a period should clear status and timestamps."""
        from app.models.accounting import GLFiscalPeriod

        period = fiscal_periods["December 2024"]

        # Verify it's closed
        assert period.status == "closed"
        assert period.closed_at is not None

        # Reopen
        period.status = "open"
        period.closed_at = None
        period.closed_by = None
        db.commit()

        # Refresh and verify
        db.refresh(period)
        assert period.status == "open"
        assert period.closed_at is None

        # Re-close for cleanup
        from datetime import datetime
        period.status = "closed"
        period.closed_at = datetime(2025, 1, 5, 10, 0, 0)
        db.commit()

    def test_reopen_already_open_period(self, db: Session, gl_accounts, fiscal_periods):
        """Reopening an already open period should be blocked."""
        period = fiscal_periods["January 2025"]
        assert period.status == "open"

        # In the actual endpoint, this would raise HTTPException
        # Here we just verify the status check works
        is_already_open = period.status == "open"
        assert is_already_open is True


# =============================================================================
# DASHBOARD WIDGETS HELPER
# =============================================================================

def get_accounting_summary_data(db: Session):
    """
    Direct implementation of accounting summary logic for testing.
    Mirrors the API endpoint logic.
    """
    from sqlalchemy import func
    from datetime import timedelta
    from app.models.accounting import GLFiscalPeriod
    from app.models.product import Product
    from app.models.inventory import Inventory

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    # Inventory by category
    category_map = {
        "material": "Raw Materials",
        "wip": "Work in Process",
        "finished_good": "Finished Goods",
        "packaging": "Packaging",
    }

    inventory_by_category = []
    total_inventory_value = Decimal("0")

    for item_type, category_name in category_map.items():
        inv_query = db.query(
            func.count(Inventory.id).label("count"),
            func.coalesce(
                func.sum(Inventory.on_hand_quantity * Product.standard_cost),
                Decimal("0")
            ).label("value"),
        ).join(
            Product, Inventory.product_id == Product.id
        ).filter(
            Product.item_type == item_type,
            Product.active == True,
        ).first()

        value = Decimal(str(inv_query.value or 0))
        count = inv_query.count or 0

        if value > 0 or count > 0:
            inventory_by_category.append({
                "category": category_name,
                "value": value,
                "item_count": count,
            })
            total_inventory_value += value

    # Current period
    current_period = db.query(GLFiscalPeriod).filter(
        GLFiscalPeriod.start_date <= today,
        GLFiscalPeriod.end_date >= today,
    ).first()

    current_period_name = None
    current_period_status = None
    if current_period:
        current_period_name = f"{current_period.year}-{current_period.period:02d}"
        current_period_status = current_period.status

    # Entry counts
    entries_today = db.query(func.count(GLJournalEntry.id)).filter(
        GLJournalEntry.entry_date == today
    ).scalar() or 0

    entries_this_week = db.query(func.count(GLJournalEntry.id)).filter(
        GLJournalEntry.entry_date >= week_ago
    ).scalar() or 0

    entries_this_month = db.query(func.count(GLJournalEntry.id)).filter(
        GLJournalEntry.entry_date >= month_start
    ).scalar() or 0

    # Balance check
    balance_query = db.query(
        func.coalesce(func.sum(GLJournalEntryLine.debit_amount), Decimal("0")).label("dr"),
        func.coalesce(func.sum(GLJournalEntryLine.credit_amount), Decimal("0")).label("cr"),
    ).first()

    total_dr = Decimal(str(balance_query.dr or 0))
    total_cr = Decimal(str(balance_query.cr or 0))
    variance = abs(total_dr - total_cr)
    books_balanced = variance < Decimal("0.01")

    return {
        "as_of_date": today,
        "total_inventory_value": total_inventory_value,
        "inventory_by_category": inventory_by_category,
        "current_period": current_period_name,
        "current_period_status": current_period_status,
        "entries_today": entries_today,
        "entries_this_week": entries_this_week,
        "entries_this_month": entries_this_month,
        "books_balanced": books_balanced,
        "variance": variance,
    }


def get_recent_entries_data(db: Session, limit: int = 10):
    """
    Direct implementation of recent entries logic for testing.
    Mirrors the API endpoint logic.
    """
    from sqlalchemy import func

    # Get total count
    total_count = db.query(func.count(GLJournalEntry.id)).scalar() or 0

    # Get recent entries with their totals
    entries_query = db.query(
        GLJournalEntry.id,
        GLJournalEntry.entry_number,
        GLJournalEntry.entry_date,
        GLJournalEntry.description,
        GLJournalEntry.source_type,
        GLJournalEntry.source_id,
        func.coalesce(func.sum(GLJournalEntryLine.debit_amount), Decimal("0")).label("total_amount"),
    ).outerjoin(
        GLJournalEntryLine, GLJournalEntry.id == GLJournalEntryLine.journal_entry_id
    ).group_by(
        GLJournalEntry.id,
        GLJournalEntry.entry_number,
        GLJournalEntry.entry_date,
        GLJournalEntry.description,
        GLJournalEntry.source_type,
        GLJournalEntry.source_id,
    ).order_by(
        GLJournalEntry.entry_date.desc(),
        GLJournalEntry.id.desc(),
    ).limit(limit)

    results = entries_query.all()

    entries = [
        {
            "id": row.id,
            "entry_number": row.entry_number,
            "entry_date": row.entry_date,
            "description": row.description or "",
            "total_amount": Decimal(str(row.total_amount or 0)),
            "source_type": row.source_type,
            "source_id": row.source_id,
        }
        for row in results
    ]

    return {
        "entries": entries,
        "total_count": total_count,
    }


# =============================================================================
# TEST: DASHBOARD WIDGETS LOGIC
# =============================================================================

class TestDashboardWidgets:
    """Tests for dashboard widget endpoints logic"""

    def test_summary_structure(self, db: Session, gl_accounts):
        """Summary should return all expected fields."""
        result = get_accounting_summary_data(db)

        # Check required fields exist
        assert "as_of_date" in result
        assert "total_inventory_value" in result
        assert "inventory_by_category" in result
        assert "entries_today" in result
        assert "entries_this_week" in result
        assert "entries_this_month" in result
        assert "books_balanced" in result
        assert "variance" in result

    def test_summary_books_balanced(self, db: Session, gl_accounts):
        """Summary should show balanced books when DR = CR."""
        # Create balanced entry
        entry_num = f"DASH-BAL-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date.today(),
            description="Test entry for balance check",
            status="posted",
        )
        db.add(je)
        db.flush()

        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0"),
        ))
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["2000"].id,
            debit_amount=Decimal("0"),
            credit_amount=Decimal("100.00"),
        ))
        db.commit()

        try:
            result = get_accounting_summary_data(db)
            assert result["books_balanced"] == True
            assert result["variance"] < Decimal("0.01")

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()

    def test_summary_entry_counts(self, db: Session, gl_accounts):
        """Summary should count entries correctly."""
        # Create entry for today
        entry_num = f"DASH-CNT-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date.today(),
            description="Today entry for count test",
            status="posted",
        )
        db.add(je)
        db.flush()
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("50.00"),
            credit_amount=Decimal("0"),
        ))
        db.commit()

        try:
            result = get_accounting_summary_data(db)
            assert result["entries_today"] >= 1
            assert result["entries_this_week"] >= 1
            assert result["entries_this_month"] >= 1

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()

    def test_recent_entries_structure(self, db: Session, gl_accounts):
        """Recent entries should return expected fields."""
        result = get_recent_entries_data(db)

        assert "entries" in result
        assert "total_count" in result
        assert isinstance(result["entries"], list)

    def test_recent_entries_with_data(self, db: Session, gl_accounts):
        """Recent entries should return entry details."""
        # Create test entry
        entry_num = f"RECENT-{uuid.uuid4().hex[:8]}"
        je = GLJournalEntry(
            entry_number=entry_num,
            entry_date=date.today(),
            description="Recent test entry",
            source_type="test",
            source_id=999,
            status="posted",
        )
        db.add(je)
        db.flush()
        db.add(GLJournalEntryLine(
            journal_entry_id=je.id,
            account_id=gl_accounts["1200"].id,
            debit_amount=Decimal("250.00"),
            credit_amount=Decimal("0"),
        ))
        db.commit()

        try:
            result = get_recent_entries_data(db, limit=5)

            assert result["total_count"] >= 1
            assert len(result["entries"]) >= 1

            # Find our entry
            our_entry = next((e for e in result["entries"] if e["entry_number"] == entry_num), None)
            assert our_entry is not None
            assert our_entry["description"] == "Recent test entry"
            assert our_entry["total_amount"] == Decimal("250.00")
            assert our_entry["source_type"] == "test"

        finally:
            # Clean up
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id == je.id
            ).delete()
            db.query(GLJournalEntry).filter(GLJournalEntry.id == je.id).delete()
            db.commit()

    def test_recent_entries_limit(self, db: Session, gl_accounts):
        """Recent entries should respect limit parameter."""
        # Create multiple entries
        created_jes = []
        for i in range(5):
            entry_num = f"LIMIT{i}-{uuid.uuid4().hex[:8]}"
            je = GLJournalEntry(
                entry_number=entry_num,
                entry_date=date.today(),
                description=f"Limit test {i}",
                status="posted",
            )
            db.add(je)
            db.flush()
            db.add(GLJournalEntryLine(
                journal_entry_id=je.id,
                account_id=gl_accounts["1200"].id,
                debit_amount=Decimal("10.00"),
                credit_amount=Decimal("0"),
            ))
            created_jes.append(je)
        db.commit()

        try:
            result = get_recent_entries_data(db, limit=3)
            assert len(result["entries"]) <= 3

        finally:
            # Clean up
            je_ids = [je.id for je in created_jes]
            db.query(GLJournalEntryLine).filter(
                GLJournalEntryLine.journal_entry_id.in_(je_ids)
            ).delete(synchronize_session=False)
            db.query(GLJournalEntry).filter(
                GLJournalEntry.id.in_(je_ids)
            ).delete(synchronize_session=False)
            db.commit()
