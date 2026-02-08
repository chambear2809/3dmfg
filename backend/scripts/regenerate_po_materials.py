"""Regenerate operation materials for a PO from its routing."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
from app.db.session import SessionLocal
from app.models.production_order import ProductionOrder, ProductionOrderOperation, ProductionOrderOperationMaterial
from app.models.manufacturing import RoutingOperationMaterial
from app.models.product import Product
from app.services.operation_generation import generate_operation_materials

db = SessionLocal()

# Get PO
po = db.query(ProductionOrder).filter(ProductionOrder.code == 'PO-2026-0001').first()
if not po:
    print("PO not found")
    exit(1)

print(f"PO: {po.code} | Qty: {po.quantity_ordered}")

# Get operations
ops = db.query(ProductionOrderOperation).filter(
    ProductionOrderOperation.production_order_id == po.id
).order_by(ProductionOrderOperation.sequence).all()

print(f"\nFound {len(ops)} operations")

for op in ops:
    print(f"\nOp {op.sequence}: {op.operation_code or 'N/A'} | routing_operation_id: {op.routing_operation_id}")

    if not op.routing_operation_id:
        print("  No routing operation linked, skipping")
        continue

    # Check if materials already exist
    existing = db.query(ProductionOrderOperationMaterial).filter(
        ProductionOrderOperationMaterial.production_order_operation_id == op.id
    ).count()

    if existing > 0:
        print(f"  Already has {existing} materials, skipping")
        continue

    # Check routing materials
    routing_mats = db.query(RoutingOperationMaterial).filter(
        RoutingOperationMaterial.routing_operation_id == op.routing_operation_id
    ).all()

    if not routing_mats:
        print("  No routing materials to copy")
        continue

    print(f"  Found {len(routing_mats)} routing materials to copy")

    # Generate materials
    created = generate_operation_materials(db, op, int(po.quantity_ordered))
    print(f"  Created {len(created)} PO operation materials")
    for mat in created:
        component = db.get(Product, mat.component_id)
        print(f"    - {component.sku if component else mat.component_id}: {mat.quantity_required} {mat.unit}")

db.commit()
print("\nDone! Materials regenerated.")
db.close()
