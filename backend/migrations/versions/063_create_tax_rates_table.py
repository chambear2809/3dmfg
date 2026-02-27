"""Create tax_rates table and add tax_name to transactional tables.

Enables multiple named tax rates (GST, QST, VAT, etc.) so international
users can configure their tax structure without forking.

Migration strategy:
- Creates tax_rates table (simple — extensible by PRO via FK)
- Adds tax_name column to quotes, sales_orders, sales_order_lines
  for human-readable display without joining tax_rates at read time
- Migrates existing CompanySettings single rate → first TaxRate row
  (only if tax_enabled=true and tax_rate IS NOT NULL and > 0)

Revision ID: 063
Revises: 062
"""
from alembic import op
import sqlalchemy as sa

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tax_rates table
    op.create_table(
        "tax_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rate", sa.Numeric(7, 4), nullable=False),  # 0.0825 for 8.25%
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tax_rates_id", "tax_rates", ["id"])
    op.create_index("ix_tax_rates_is_default", "tax_rates", ["is_default"])

    # Add tax_name to transactional tables for display (human-readable snapshot)
    op.add_column("quotes", sa.Column("tax_name", sa.String(100), nullable=True))
    op.add_column("sales_orders", sa.Column("tax_name", sa.String(100), nullable=True))
    op.add_column("sales_order_lines", sa.Column("tax_name", sa.String(100), nullable=True))

    # Migrate existing CompanySettings single tax rate → TaxRate default row
    op.execute("""
        INSERT INTO tax_rates (name, rate, is_default, is_active, created_at, updated_at)
        SELECT
            COALESCE(tax_name, 'Sales Tax'),
            tax_rate,
            true,
            true,
            NOW(),
            NOW()
        FROM company_settings
        WHERE id = 1
          AND tax_enabled = true
          AND tax_rate IS NOT NULL
          AND tax_rate > 0
    """)


def downgrade() -> None:
    op.drop_column("sales_order_lines", "tax_name")
    op.drop_column("sales_orders", "tax_name")
    op.drop_column("quotes", "tax_name")
    op.drop_index("ix_tax_rates_is_default", table_name="tax_rates")
    op.drop_index("ix_tax_rates_id", table_name="tax_rates")
    op.drop_table("tax_rates")
