"""
API v1 Router - FilaOps Open Source Core

Authorization strategy:
  Most routers use ``staff_dependencies`` (router-level guard requiring staff).
  Routers WITHOUT router-level staff_dependencies enforce auth per-endpoint:

  - auth:           Public (login, register, password reset)
  - assets:         Public (product image serving for catalog display)
  - setup:          Public (first-run only; backend rejects if admin exists)
  - sales_orders:   Per-endpoint get_current_user + owner-or-staff checks
  - materials:      Mixed public catalog + staff-only management endpoints
  - accounting:     Per-endpoint get_current_admin_user
  - system:         /version and /info are public (frontend bootstrap);
                    /updates/* require staff; /health is public (probes)
  - command_center: Per-endpoint get_current_admin_user
  - test:           Dev-only (gated by is_production)
"""
import os
from fastapi import APIRouter, Depends
from app.core.config import settings as app_settings
from app.api.v1.endpoints import (
    accounting,
    assets,
    scheduling,
    auth,
    sales_orders,
    production_orders,
    operation_status,
    inventory,
    products,
    items,
    materials,
    vendors,
    purchase_orders,
    po_documents,
    low_stock,
    vendor_items,
    work_centers,
    resources,
    routings,
    mrp,
    setup,
    quotes,
    settings,
    payments,
    printers,
    tax_rates,
    system,
    spools,
    traceability,
    maintenance,
    command_center,
    security,
    invoices,
    notifications,
)
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.deps import get_current_staff_user

router = APIRouter()
staff_dependencies = [Depends(get_current_staff_user)]

# Authentication
router.include_router(auth.router)

# Asset proxy endpoints
router.include_router(assets.router)

# First-run setup (creates initial admin)
router.include_router(setup.router)

# Sales Orders
router.include_router(sales_orders.router)

# Quotes
router.include_router(quotes.router, dependencies=staff_dependencies)

# Products
router.include_router(
    products.router,
    prefix="/products",
    tags=["products"],
    dependencies=staff_dependencies,
)

# Items (unified item management)
router.include_router(
    items.router,
    prefix="/items",
    tags=["items"],
    dependencies=staff_dependencies,
)

# Production Orders
router.include_router(
    production_orders.router,
    prefix="/production-orders",
    tags=["production"],
    dependencies=staff_dependencies,
)

# Operation Status (nested under production orders)
router.include_router(
    operation_status.router,
    prefix="/production-orders",
    tags=["production-operations"],
    dependencies=staff_dependencies,
)

# Inventory
router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["inventory"],
    dependencies=staff_dependencies,
)

# Materials
router.include_router(
    materials.router,
    prefix="/materials",
    tags=["materials"]
)

# Admin (BOM management, dashboard, traceability)
router.include_router(
    admin_router,
    prefix="/admin",
    tags=["admin"],
    dependencies=staff_dependencies,
)

# Vendors
router.include_router(
    vendors.router,
    prefix="/vendors",
    tags=["vendors"],
    dependencies=staff_dependencies,
)

# Purchase Orders
router.include_router(
    purchase_orders.router,
    prefix="/purchase-orders",
    tags=["purchase-orders"],
    dependencies=staff_dependencies,
)

# Purchase Order Documents (multi-file upload)
router.include_router(
    po_documents.router,
    prefix="/purchase-orders",
    tags=["purchase-orders"],
    dependencies=staff_dependencies,
)

# Low Stock Workflow (create POs from low stock)
router.include_router(
    low_stock.router,
    prefix="/purchase-orders",
    tags=["purchase-orders"],
    dependencies=staff_dependencies,
)

# Vendor Items (SKU mapping for invoice parsing)
router.include_router(
    vendor_items.router,
    prefix="/purchase-orders",
    tags=["purchase-orders"],
    dependencies=staff_dependencies,
)

# Invoices (Core billing)
router.include_router(invoices.router, dependencies=staff_dependencies)

# Notifications (operator messaging)
router.include_router(notifications.router, dependencies=staff_dependencies)

# Invoice Import is a PRO feature
# Exports (QuickBooks) is a PRO feature
# Amazon Import is a PRO feature

# Work Centers
router.include_router(
    work_centers.router,
    prefix="/work-centers",
    tags=["manufacturing"],
    dependencies=staff_dependencies,
)

# Resources (scheduling and conflicts)
router.include_router(
    resources.router,
    prefix="/resources",
    tags=["manufacturing"],
    dependencies=staff_dependencies,
)

# Routings
router.include_router(
    routings.router,
    prefix="/routings",
    tags=["manufacturing"],
    dependencies=staff_dependencies,
)

# B2B Portal API is a PRO feature

# MRP (Material Requirements Planning)
router.include_router(mrp.router, dependencies=staff_dependencies)

# Features/Licensing is a PRO feature

# Scheduling and Capacity Management
router.include_router(
    scheduling.router,
    prefix="/scheduling",
    tags=["scheduling"],
    dependencies=staff_dependencies,
)

# Company Settings
router.include_router(settings.router, dependencies=staff_dependencies)

# Tax Rates (multi-rate i18n support)
router.include_router(tax_rates.router, dependencies=staff_dependencies)

# Payments
router.include_router(payments.router, dependencies=staff_dependencies)

# GL Accounting (Trial Balance, Inventory Valuation)
router.include_router(
    accounting.router,
    prefix="/accounting",
    tags=["accounting"]
)

# Printers
router.include_router(
    printers.router,
    prefix="/printers",
    tags=["printers"],
    dependencies=staff_dependencies,
)

# System (version, updates, health)
router.include_router(system.router)

# Security Audit
router.include_router(security.router, dependencies=staff_dependencies)

# Material Spools
router.include_router(spools.router, dependencies=staff_dependencies)

# Quality - Traceability
router.include_router(
    traceability.router,
    prefix="/traceability",
    tags=["quality"],
    dependencies=staff_dependencies,
)

# Maintenance
router.include_router(
    maintenance.router,
    prefix="/maintenance",
    tags=["maintenance"],
    dependencies=staff_dependencies,
)

# Command Center (dashboard)
router.include_router(
    command_center.router,
    prefix="/command-center",
    tags=["command-center"]
)

# License activation is a PRO feature

# Test endpoints - only enabled in non-production environments
# These endpoints allow E2E tests to seed test data
if not app_settings.is_production:
    from app.api.v1.endpoints import test as test_endpoints
    router.include_router(test_endpoints.router)
