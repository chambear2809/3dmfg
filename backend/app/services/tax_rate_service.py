"""
Tax Rate Service — CRUD for named tax rates.

Resolution pattern used by quote/order creation:
  1. If specific tax_rate_id passed → use that TaxRate
  2. If apply_tax=True → use get_default_tax_rate() (first active default)
  3. Fall back to CompanySettings.tax_rate (legacy single-rate)
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.tax_rate import TaxRate

logger = get_logger(__name__)


def list_tax_rates(db: Session, *, active_only: bool = True) -> list[TaxRate]:
    query = db.query(TaxRate)
    if active_only:
        query = query.filter(TaxRate.is_active == True)
    return query.order_by(TaxRate.is_default.desc(), TaxRate.name).all()


def get_tax_rate(db: Session, tax_rate_id: int) -> TaxRate:
    rate = db.query(TaxRate).filter(TaxRate.id == tax_rate_id).first()
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax rate not found")
    return rate


def get_default_tax_rate(db: Session) -> Optional[TaxRate]:
    """Return the active default tax rate, or None if none configured."""
    return (
        db.query(TaxRate)
        .filter(TaxRate.is_default == True, TaxRate.is_active == True)
        .first()
    )


def create_tax_rate(
    db: Session,
    *,
    name: str,
    rate: Decimal,
    description: Optional[str] = None,
    is_default: bool = False,
) -> TaxRate:
    if is_default:
        _clear_default(db)
    tax_rate = TaxRate(name=name, rate=rate, description=description, is_default=is_default)
    db.add(tax_rate)
    db.commit()
    db.refresh(tax_rate)
    logger.info("Created tax rate %r (%.4f) is_default=%s", name, float(rate), is_default)
    return tax_rate


def update_tax_rate(db: Session, tax_rate_id: int, **kwargs) -> TaxRate:
    rate = get_tax_rate(db, tax_rate_id)
    if kwargs.get("is_default"):
        _clear_default(db)
    for k, v in kwargs.items():
        if v is not None:
            setattr(rate, k, v)
    rate.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(rate)
    return rate


def delete_tax_rate(db: Session, tax_rate_id: int) -> None:
    """Soft-delete: deactivate instead of removing so historical records remain valid."""
    rate = get_tax_rate(db, tax_rate_id)
    rate.is_active = False
    rate.is_default = False
    rate.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    logger.info("Deactivated tax rate id=%d (%r)", tax_rate_id, rate.name)


def _clear_default(db: Session) -> None:
    """Remove is_default from any currently-default rates before setting a new one."""
    db.query(TaxRate).filter(TaxRate.is_default == True).update({"is_default": False})
