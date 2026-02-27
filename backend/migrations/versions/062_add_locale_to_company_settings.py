"""Add locale column for i18n support.

Adds locale (BCP-47 string, e.g. "en-US", "fr-CA", "ar-SA") to company_settings.
Also backfills currency_code which already exists in the model but may be NULL
in existing rows.

Revision ID: 062
Revises: 061
"""
from alembic import op
import sqlalchemy as sa

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_settings",
        sa.Column("locale", sa.String(20), nullable=True),
    )
    # Backfill existing rows to sane defaults
    op.execute("UPDATE company_settings SET locale = 'en-US' WHERE locale IS NULL")
    op.execute("UPDATE company_settings SET currency_code = 'USD' WHERE currency_code IS NULL")


def downgrade() -> None:
    op.drop_column("company_settings", "locale")
