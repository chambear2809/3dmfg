"""TaxRate model — named tax rates for multi-rate international support.

Design decisions:
- No FK from Quote/SalesOrder to TaxRate: tax_rate (decimal) + tax_name (string)
  are stored as frozen snapshots on each transaction for audit immutability.
  If a rate changes, historical transactions are unaffected.
- PRO can add a tax_jurisdictions table that FKs to tax_rates.id without
  modifying this table (Core schema extensibility rule).
- is_active is a soft-delete — deactivated rates remain for historical reference.
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, func

from app.db.base import Base


class TaxRate(Base):
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # "Sales Tax", "GST", "VAT 20%"
    rate = Column(Numeric(7, 4), nullable=False)  # 0.0825 for 8.25%
    description = Column(String(500), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<TaxRate(id={self.id}, name={self.name!r}, rate={self.rate})>"
