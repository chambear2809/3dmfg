# God Files Analysis — ARCHITECT-002

**Status: Completed (v3.2.0)** — The refactoring described in this document has been largely completed. See CHANGELOG.md for details of what was actually implemented, which differs from some of the extraction plans below.

## Summary

| File | Lines | useState | Sub-components | Recommended Splits |
|------|-------|----------|----------------|-------------------|
| AdminPurchasing.jsx | 1,427 | 26 | 4 tabs inline | Extract 4 tab components + ImportModal |
| SalesOrderWizard.jsx | 1,418 | 27 | Wizard steps inline | Extract ProductSearchGrid, OrderLineItemsTable, step shells |
| BOMDetailView.jsx | 1,105 | 25+ | 4 modals, routing section | Extract modals, CostRollupCard, routing section |
| AdminItems.jsx | 1,069 | 20 | 8 modals, sidebar | Extract sidebar, stats grid, filter bar, bulk toolbar |
| AdminDashboard.jsx | 1,025 | ~15 | SalesChart 450+ lines | Extract SalesChart, ProductionPipeline, dateUtils |
| RoutingEditor.jsx | 1,025 | ~18 | Nested operation rows | Extract RoutingOperationRow, AddOperationForm |
| ItemWizard.jsx | 1,015 | ~20 | Multi-step form | Extract BasicInfoStep, BOMBuilder, PricingStep |

No files exceed the original 2000-line threshold. All 7 files are in the 1,000–1,427 line range.

---

## AdminPurchasing.jsx (1,427 lines)

- **Path:** `frontend/src/components/admin/AdminPurchasing.jsx`
- **Hooks:** 26 useState, plus useEffect, useMemo
- **Structure:** Single component with 4 tab panels rendered inline via conditional logic
- **Tabs:** Low Stock, Purchase Orders, Vendors, Import
- **Natural boundaries:**
  - Each tab is self-contained (own state, own API calls)
  - Import tab has a modal that can be extracted
  - Stats summary at top is shared across tabs
- **Extraction plan:**
  1. `LowStockTab` — low stock alerts table + reorder logic
  2. `PurchaseOrdersTab` — PO list, status management
  3. `VendorsTab` — vendor CRUD
  4. `ImportTab` — CSV import modal and upload logic
  5. Parent becomes thin orchestrator (~200 lines): tab state, shared stats fetch

## SalesOrderWizard.jsx (1,418 lines)

- **Path:** `frontend/src/components/admin/SalesOrderWizard.jsx`
- **Hooks:** 27 useState, useCallback, useMemo, useEffect
- **Structure:** Multi-step wizard (customer select → product search → line items → review → submit)
- **Natural boundaries:**
  - Product search grid with filters (~300 lines)
  - Order line items table with inline editing (~250 lines)
  - Review/summary section
  - Wizard navigation header/footer
- **Extraction plan:**
  1. `ProductSearchGrid` — search input, filters, product cards/table
  2. `OrderLineItemsTable` — line items with quantity/price editing
  3. `OrderReviewSummary` — final review before submit
  4. Parent keeps wizard step state + submission logic (~300 lines)

## BOMDetailView.jsx (1,105 lines)

- **Path:** `frontend/src/components/admin/BOMDetailView.jsx`
- **Hooks:** 25+ state hooks
- **Structure:** BOM detail page with inline editing, modals, routing section, cost rollup
- **Modals:** Add Line, Edit Line, Import BOM, Version History (4 modals)
- **Natural boundaries:**
  - Routing section (~200 lines) — separate concern from BOM lines
  - Cost rollup card (~150 lines)
  - Each modal is self-contained
- **Extraction plan:**
  1. `BOMRoutingSection` — routing operations display/edit
  2. `CostRollupCard` — cost calculation display
  3. `AddBOMLineModal` / `EditBOMLineModal` — modals
  4. Parent keeps BOM line table + header (~500 lines)

## AdminItems.jsx (1,069 lines)

- **Path:** `frontend/src/components/admin/AdminItems.jsx`
- **Hooks:** 20 useState
- **Structure:** Product catalog management with list view, filters, bulk operations, 8 modals
- **Natural boundaries:**
  - Sidebar filters (~150 lines)
  - Stats grid (~100 lines)
  - Filter/search bar (~120 lines)
  - Bulk action toolbar
  - Multiple modals (create, edit, clone, archive, etc.)
- **Extraction plan:**
  1. `ItemFilterSidebar` — category/status/type filters
  2. `ItemStatsGrid` — summary statistics cards
  3. `ItemBulkToolbar` — bulk selection actions
  4. Consolidate small modals into `ItemModals.jsx`
  5. Parent keeps table + state orchestration (~400 lines)

## AdminDashboard.jsx (1,025 lines)

- **Path:** `frontend/src/components/admin/AdminDashboard.jsx`
- **Hooks:** ~15 useState
- **Structure:** Dashboard with KPI cards, sales chart (450+ lines inline), production pipeline
- **Natural boundaries:**
  - Sales chart is a clear extraction target (largest inline section)
  - Production pipeline section
  - Date range utilities
- **Extraction plan:**
  1. `SalesChart` — chart component with its own data fetching (~450 lines)
  2. `ProductionPipelineCard` — production order pipeline widget
  3. Parent keeps KPI cards + layout (~300 lines)

## RoutingEditor.jsx (1,025 lines)

- **Path:** `frontend/src/components/admin/RoutingEditor.jsx`
- **Hooks:** ~18 useState
- **Structure:** Routing operations editor with nested rows, drag-reorder, inline editing
- **Natural boundaries:**
  - Operation row component (repeated for each operation)
  - Add operation form
  - Operation detail modal
- **Extraction plan:**
  1. `RoutingOperationRow` — single operation row with inline editing
  2. `AddOperationForm` — form for adding new operations
  3. Parent keeps operation list state + drag logic (~400 lines)

## ItemWizard.jsx (1,015 lines)

- **Path:** `frontend/src/components/admin/ItemWizard.jsx`
- **Hooks:** ~20 useState
- **Structure:** Multi-step product creation wizard (basic info → BOM → pricing → review)
- **Natural boundaries:**
  - Each wizard step is a natural component
  - BOM builder section is complex enough to extract
  - Pricing step with cost calculations
- **Extraction plan:**
  1. `BasicInfoStep` — product name, SKU, category, description
  2. `BOMBuilderStep` — BOM line management during creation
  3. `PricingStep` — cost, margin, selling price calculations
  4. Parent keeps wizard navigation + submit logic (~250 lines)

---

## Priority Order

1. **AdminPurchasing.jsx** (1,427) — largest, clean tab boundaries
2. **SalesOrderWizard.jsx** (1,418) — second largest, clear step boundaries
3. **BOMDetailView.jsx** (1,105) — modals easy to extract
4. **AdminItems.jsx** (1,069) — many small extractions
5. **AdminDashboard.jsx** (1,025) — SalesChart is biggest win
6. **RoutingEditor.jsx** (1,025) — operation rows are natural components
7. **ItemWizard.jsx** (1,015) — wizard steps are clean boundaries
