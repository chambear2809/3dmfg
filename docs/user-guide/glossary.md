# Glossary

> Key terms used throughout FilaOps and this manual.

---

| Term | Definition |
|------|-----------|
| **Adjustment** | A manual inventory transaction that increases or decreases an item's quantity. Used to correct discrepancies found during cycle counts or to account for waste. |
| **Bill of Materials (BOM)** | A list of raw materials and components — with quantities — needed to produce one unit of a finished product. BOMs drive both MRP calculations and cost estimates. |
| **COGS (Cost of Goods Sold)** | The total cost of materials and labor that went into producing items that were sold. Calculated from BOMs and production records. |
| **Command Center** | A dedicated monitoring page (`/admin/command-center`) that shows real-time production status, action items, overdue operations, and machine status. |
| **Confirmed (Order)** | A sales order that has been accepted and is ready for production and fulfillment. Confirmed orders create demand for MRP. |
| **Consumption** | An inventory transaction that removes material from stock when it's used in production. Consumption quantities come from the BOM. |
| **Cycle Count** | A process of counting physical inventory and comparing it to system quantities. Used to correct discrepancies without shutting down operations. |
| **Dashboard** | The main landing page after login. Shows key metrics including open orders, production status, revenue trends, and low stock alerts. |
| **Draft (Order)** | A sales order that's been started but not yet confirmed. Draft orders don't create demand and won't appear in MRP unless you opt in. |
| **Draft (Production)** | A production order that's been created but not yet started. Materials haven't been consumed. |
| **ERP** | Enterprise Resource Planning. A system that manages core business processes — inventory, production, purchasing, sales, and accounting — in one place. FilaOps is an ERP designed for 3D print farms. |
| **Finished Good** | A product that's ready to sell. Finished goods are manufactured from raw materials using a BOM and routing. |
| **Firmed (Planned Order)** | An MRP-generated planned purchase order that you've approved. Firmed orders are ready to be released as actual purchase orders. |
| **Fleet Management** | The section of FilaOps that tracks your 3D printers — their status, maintenance schedules, and network connections. |
| **Gross Margin** | Revenue minus COGS, expressed as a percentage. Shows how much profit you make on each dollar of sales before overhead. |
| **Gross Profit** | Revenue minus COGS, expressed as a dollar amount. |
| **In Progress (Production)** | A production order that has been started. Materials are being consumed and operations are being performed. |
| **Inventory Transaction** | Any event that changes an item's quantity — receipts, consumption, adjustments, or shipments. All transactions are recorded and auditable. |
| **Item** | Any product, material, or component tracked in FilaOps. Items can be raw materials (filament, hardware), finished goods, or components. |
| **Lead Time** | The number of days between placing a purchase order with a vendor and receiving the materials. Used by MRP to calculate when to order. |
| **Location** | A physical place where inventory is stored — a warehouse, shelf, bin, staging area, or quality control zone. Locations can be nested (e.g., a shelf inside a warehouse). |
| **Lot** | A batch identifier that traces materials back to a specific purchase or production run. Used for quality control and recall management. |
| **MQTT** | Message Queuing Telemetry Transport. A lightweight messaging protocol used by many 3D printers to publish their status in real time. FilaOps can subscribe to MQTT topics to monitor printer status. |
| **MRP (Material Requirements Planning)** | A planning tool that calculates what materials you need, in what quantities, and when — based on sales order demand, current inventory, and BOMs. |
| **Net Shortage** | The difference between what MRP says you need and what you currently have. A positive shortage means you need to order materials. |
| **OctoPrint** | Popular open-source 3D printer management software. FilaOps can discover and connect to printers running OctoPrint. |
| **Operation** | A single step in a routing — like "Print," "Remove supports," "Sand," or "Package." Each operation has an estimated time and is assigned to a work center. |
| **Operator** | A user role in FilaOps with permissions focused on day-to-day production tasks. Operators can't change system settings or manage other users. |
| **Planned Order** | An MRP-generated suggestion to purchase materials. Planned orders need to be firmed and then released before they become actual purchase orders. |
| **Planning Horizon** | The number of days ahead that MRP looks when calculating material needs. A 14-day horizon plans two weeks of material requirements. |
| **Purchase Order (PO)** | A formal request to a vendor to supply materials at a specified price and quantity. POs track what you've ordered, what's been received, and what's outstanding. |
| **Quote** | A price estimate sent to a customer before they commit to an order. Quotes can be converted to sales orders when accepted. |
| **Raw Material** | An input item used in production — filament, screws, packaging, etc. Raw materials appear in BOMs and are consumed during manufacturing. |
| **Receipt** | An inventory transaction that adds materials to stock, typically when a purchase order delivery arrives. |
| **Reorder Point** | The minimum inventory level that triggers a restock alert. When on-hand quantity drops below this number, the item appears in the Low Stock list. |
| **Routing** | The sequence of operations needed to manufacture a product. Routes define the steps, order, work centers, and estimated times for production. |
| **Safety Stock** | Extra inventory kept on hand as a buffer against unexpected demand or supply delays. MRP considers safety stock when calculating requirements. |
| **Sales Order** | A confirmed commitment from a customer to purchase products at agreed prices. Sales orders drive production planning, inventory allocation, and revenue recognition. |
| **Scrap** | A production outcome where the manufactured item fails quality standards and can't be sold. Scrapped production orders record a scrap reason for tracking and analysis. |
| **Scrap Reason** | A predefined code that explains why a production order was scrapped (e.g., "print_failure," "wrong_material," "damaged_in_post"). Configured in System Settings. |
| **Serial Number** | A unique identifier assigned to an individual finished product. Used for warranty tracking and customer support. |
| **Ship** | The action of marking a sales order as delivered to the customer. Shipping triggers revenue recognition and inventory deduction in FilaOps. |
| **SKU (Stock Keeping Unit)** | A unique code that identifies a specific item in your catalog. Often used for barcode scanning and external system integration. |
| **Spool** | A roll of 3D printing filament tracked individually in FilaOps. Spools have properties like material type, color, weight remaining, and location. |
| **Tax Center** | The accounting tab that summarizes tax collected on shipped orders, broken down by tax rate and time period. |
| **UOM (Unit of Measure)** | The unit used to track an item's quantity — each, gram, kilogram, meter, liter, etc. FilaOps uses a dual-UOM system for materials: a storage unit (e.g., G for grams) for inventory tracking, and a purchase unit (e.g., KG for kilograms) for buying. The `purchase_factor` converts between them (1 KG = 1000 G). Costs are stored per purchase unit ($/KG) and divided by `purchase_factor` for per-storage-unit costs ($/G). |
| **Vendor** | A supplier that provides raw materials or components. Vendors are linked to purchase orders and can have lead times, payment terms, and contact information. |
| **Work Center** | A production resource — typically a 3D printer, post-processing station, or assembly area. Work centers have capacity and are assigned to routing operations. |
