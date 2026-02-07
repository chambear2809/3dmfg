"""
Export functionality for products, orders, inventory

Business logic lives in ``app.services.export_service``.
"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.deps import get_current_staff_user
from app.core.limiter import limiter
from app.models.user import User
from app.services import export_service as svc
from app.services.export_service import sanitize_csv_field as _san

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/products")
@limiter.limit("30/minute")  # type: ignore
async def export_products(
    request: Request,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Export products to CSV."""
    rows = svc.get_products_for_export(db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "SKU", "Name", "Description", "Item Type", "Procurement Type",
        "Unit", "Standard Cost", "Selling Price", "On Hand Qty",
        "Reorder Point", "Active",
    ])
    for r in rows:
        writer.writerow([
            _san(r["sku"]), _san(r["name"]), _san(r["description"]),
            _san(r["item_type"]), _san(r["procurement_type"]), _san(r["unit"]),
            r["standard_cost"], r["selling_price"], r["on_hand_qty"],
            r["reorder_point"], r["active"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=products_export_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


@router.get("/orders")
@limiter.limit("30/minute")  # type: ignore
async def export_orders(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """Export sales orders to CSV."""
    rows = svc.get_orders_for_export(db, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order Number", "Customer", "Status", "Total", "Created Date", "Line Items",
    ])
    for r in rows:
        writer.writerow([
            _san(r["order_number"]), _san(r["customer"]), _san(r["status"]),
            r["total"], r["created_at"], _san(r["line_items"]),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=orders_export_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )
