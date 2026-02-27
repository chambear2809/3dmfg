"""
Create adjustment_reasons table and seed default data.

Provides configurable reasons for inventory adjustments,
similar to scrap_reasons for production scrapping.

Revision ID: 058_adjustment_reasons
Revises: 057_seed_scrap_reasons
Create Date: 2026-02-08
"""
from alembic import op
from sqlalchemy import text

# revision identifiers
revision = '058_adjustment_reasons'
down_revision = '057_seed_scrap_reasons'
branch_labels = None
depends_on = None


def upgrade():
    """Create adjustment_reasons table and seed default data."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS adjustment_reasons (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT TRUE NOT NULL,
            sequence INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_adjustment_reasons_code ON adjustment_reasons (code);
        CREATE INDEX IF NOT EXISTS ix_adjustment_reasons_id ON adjustment_reasons (id);
    """)

    op.execute("""
        INSERT INTO adjustment_reasons (code, name, description, active, sequence, created_at, updated_at) VALUES
        ('physical_count', 'Physical Count', 'Discrepancy found during physical inventory count', true, 10, NOW(), NOW()),
        ('cycle_count', 'Cycle Count', 'Adjustment from cycle counting process', true, 20, NOW(), NOW()),
        ('correction', 'Data Correction', 'Correcting a data entry error', true, 30, NOW(), NOW()),
        ('damaged', 'Damaged Goods', 'Item damaged in storage or handling', true, 40, NOW(), NOW()),
        ('found', 'Found Inventory', 'Previously unaccounted inventory discovered', true, 50, NOW(), NOW()),
        ('theft_loss', 'Theft/Loss', 'Inventory missing due to theft or unexplained loss', true, 60, NOW(), NOW()),
        ('expired', 'Expired/Obsolete', 'Item past usable life or obsolete', true, 70, NOW(), NOW()),
        ('reclassification', 'Reclassification', 'Item moved to different category or account', true, 80, NOW(), NOW()),
        ('other', 'Other', 'Other adjustment reason - specify in notes', true, 90, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade():
    """Drop adjustment_reasons table."""
    op.execute("DROP TABLE IF EXISTS adjustment_reasons;")
