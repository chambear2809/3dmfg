"""
Seed Customer Test Data for FilaOps

Creates sample customer records (as User objects with account_type='customer')
for testing the admin customer management UI.

Run from backend directory:
    python scripts/seed_customers.py
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password
import secrets


# =============================================================================
# Test Data
#
# NOTE: The admin UI manages customers as User records with
# account_type='customer'. Each entry below becomes a row in the users table.
# =============================================================================

CUSTOMERS = [
    {
        "customer_number": "CUST-001",
        "email": "john@acmemfg.com",
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Acme Manufacturing",
        "phone": "555-100-1000",
        "status": "active",
        "billing_address_line1": "100 Industrial Blvd",
        "billing_city": "Detroit",
        "billing_state": "MI",
        "billing_zip": "48201",
        "billing_country": "USA",
        "shipping_address_line1": "100 Industrial Blvd",
        "shipping_city": "Detroit",
        "shipping_state": "MI",
        "shipping_zip": "48201",
        "shipping_country": "USA",
    },
    {
        "customer_number": "CUST-002",
        "email": "sarah@makerspacepdx.org",
        "first_name": "Sarah",
        "last_name": "Chen",
        "company_name": "MakerSpace PDX",
        "phone": "503-555-0200",
        "status": "active",
        "billing_address_line1": "420 SE Hawthorne Blvd",
        "billing_city": "Portland",
        "billing_state": "OR",
        "billing_zip": "97214",
        "billing_country": "USA",
        "shipping_address_line1": "420 SE Hawthorne Blvd",
        "shipping_city": "Portland",
        "shipping_state": "OR",
        "shipping_zip": "97214",
        "shipping_country": "USA",
    },
    {
        "customer_number": "CUST-003",
        "email": "mike.rivera@gmail.com",
        "first_name": "Mike",
        "last_name": "Rivera",
        "phone": "415-555-0300",
        "status": "active",
        "billing_address_line1": "789 Mission St Apt 4B",
        "billing_city": "San Francisco",
        "billing_state": "CA",
        "billing_zip": "94103",
        "billing_country": "USA",
        "shipping_address_line1": "789 Mission St Apt 4B",
        "shipping_city": "San Francisco",
        "shipping_state": "CA",
        "shipping_zip": "94103",
        "shipping_country": "USA",
    },
    {
        "customer_number": "CUST-004",
        "email": "lisa@robotechsolutions.com",
        "first_name": "Lisa",
        "last_name": "Patel",
        "company_name": "RoboTech Solutions",
        "phone": "512-555-0400",
        "status": "active",
        "billing_address_line1": "2200 Tech Ridge Pkwy",
        "billing_address_line2": "Suite 300",
        "billing_city": "Austin",
        "billing_state": "TX",
        "billing_zip": "78728",
        "billing_country": "USA",
        "shipping_address_line1": "2200 Tech Ridge Pkwy",
        "shipping_address_line2": "Suite 300",
        "shipping_city": "Austin",
        "shipping_state": "TX",
        "shipping_zip": "78728",
        "shipping_country": "USA",
    },
    {
        "customer_number": "CUST-005",
        "email": "alex@cosplaycreations.net",
        "first_name": "Alex",
        "last_name": "Kim",
        "company_name": "Cosplay Creations",
        "phone": "206-555-0500",
        "status": "active",
        "billing_address_line1": "1500 Pike Place",
        "billing_city": "Seattle",
        "billing_state": "WA",
        "billing_zip": "98101",
        "billing_country": "USA",
        "shipping_address_line1": "1500 Pike Place",
        "shipping_city": "Seattle",
        "shipping_state": "WA",
        "shipping_zip": "98101",
        "shipping_country": "USA",
    },
    {
        "customer_number": "CUST-006",
        "email": "carlos@dronedynamics.io",
        "first_name": "Carlos",
        "last_name": "Mendez",
        "company_name": "Drone Dynamics LLC",
        "phone": "720-555-0600",
        "status": "inactive",
        "billing_address_line1": "850 Walnut St",
        "billing_city": "Boulder",
        "billing_state": "CO",
        "billing_zip": "80302",
        "billing_country": "USA",
        "shipping_address_line1": "850 Walnut St",
        "shipping_city": "Boulder",
        "shipping_state": "CO",
        "shipping_zip": "80302",
        "shipping_country": "USA",
    },
]


# =============================================================================
# Seed Function
# =============================================================================

def seed_customers(db: Session) -> tuple[int, int]:
    """Seed customer records as User objects. Returns (created, skipped) counts."""
    created = 0
    skipped = 0

    for cust_data in CUSTOMERS:
        # Check by email (unique constraint on users table)
        existing = db.query(User).filter(User.email == cust_data["email"]).first()

        if existing:
            label = cust_data.get("company_name") or f"{cust_data['first_name']} {cust_data['last_name']}"
            print(f"  SKIP  {cust_data['customer_number']} ({label}) - email already exists")
            skipped += 1
            continue

        # Random unusable password (customers are CRM records, no portal login in core)
        password_hash = hash_password(secrets.token_urlsafe(32))

        customer = User(
            account_type="customer",
            email_verified=False,
            password_hash=password_hash,
            **cust_data,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        label = cust_data.get("company_name") or f"{cust_data['first_name']} {cust_data['last_name']}"
        print(f"  OK    {cust_data['customer_number']} - {label}")
        created += 1

    return created, skipped


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("FilaOps Customer Data Seeder")
    print("=" * 60)

    db = SessionLocal()

    try:
        print("\nSeeding customers...")
        created, skipped = seed_customers(db)

        print("\n" + "=" * 60)
        print(f"Done: {created} created, {skipped} skipped")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
