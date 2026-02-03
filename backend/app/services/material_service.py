"""
Material Service

Handles material lookups, availability checks, and pricing for the quote-to-order workflow.
This is the central service for mapping customer material/color selections to actual inventory.

CSV import and color creation added (ARCHITECT-003).
"""
import csv
import io
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.logging_config import get_logger
from app.models.material import MaterialType, Color, MaterialColor, MaterialInventory
from app.models.product import Product
from app.models.inventory import Inventory, InventoryLocation
from app.models.item_category import ItemCategory

logger = get_logger(__name__)


class MaterialNotFoundError(Exception):
    """Raised when a material type is not found"""
    pass


class ColorNotFoundError(Exception):
    """Raised when a color is not found"""
    pass


class MaterialColorNotAvailableError(Exception):
    """Raised when a material-color combination is not available"""
    pass


class MaterialNotInStockError(Exception):
    """Raised when a material-color combination is not in stock"""
    pass


def resolve_material_code(db: Session, code: str) -> str:
    """
    Resolve a simple material name to its full database code.

    The portal UI sends simple names like 'PLA', 'PETG', etc.
    The database uses specific codes like 'PLA_BASIC', 'PETG_HF'.

    This function handles the mapping:
    - 'PLA' -> 'PLA_BASIC' (default PLA variant)
    - 'PETG' -> 'PETG_HF' (default PETG variant)
    - 'PLA_BASIC' -> 'PLA_BASIC' (already full code, pass through)

    Args:
        db: Database session
        code: Material code from portal (simple or full)

    Returns:
        Full material type code

    Raises:
        MaterialNotFoundError: If no matching material found
    """
    code_upper = code.upper()

    # First try exact match (already a full code)
    material = db.query(MaterialType).filter(
        MaterialType.code == code_upper,
        MaterialType.active.is_(True)
    ).first()

    if material:
        return material.code

    # Try matching by base_material (e.g., 'PLA' matches base_material='PLA')
    material = db.query(MaterialType).filter(
        MaterialType.base_material == code_upper,
        MaterialType.active.is_(True),  # noqa: E712
        MaterialType.is_customer_visible.is_(True)  # Prefer customer-visible variants
    ).order_by(MaterialType.display_order).first()

    if material:
        return material.code

    # Fallback: Try without customer_visible filter
    material = db.query(MaterialType).filter(
        MaterialType.base_material == code_upper,
        MaterialType.active.is_(True)
    ).order_by(MaterialType.display_order).first()

    if material:
        return material.code

    raise MaterialNotFoundError(f"Material type not found: {code}")


def get_material_type(db: Session, code: str) -> MaterialType:
    """
    Get a material type by code

    Args:
        db: Database session
        code: Material type code (e.g., 'PLA_BASIC', 'PETG_HF') or simple name ('PLA', 'PETG')

    Returns:
        MaterialType object

    Raises:
        MaterialNotFoundError: If material type not found
    """
    # Resolve simple names to full codes
    resolved_code = resolve_material_code(db, code)

    material = db.query(MaterialType).filter(
        MaterialType.code == resolved_code,
        MaterialType.active.is_(True)
    ).first()

    if not material:
        raise MaterialNotFoundError(f"Material type not found: {code}")

    return material


def get_color(db: Session, code: str) -> Color:
    """
    Get a color by code
    
    Args:
        db: Database session
        code: Color code (e.g., 'BLK', 'WHT', 'CHARCOAL')
    
    Returns:
        Color object
    
    Raises:
        ColorNotFoundError: If color not found
    """
    color = db.query(Color).filter(
        Color.code == code,
        Color.active.is_(True)
    ).first()
    
    if not color:
        raise ColorNotFoundError(f"Color not found: {code}")
    
    return color


def get_available_material_types(db: Session, customer_visible_only: bool = True) -> List[MaterialType]:
    """
    Get all available material types for dropdown
    
    Args:
        db: Database session
        customer_visible_only: If True, only return customer-visible materials
    
    Returns:
        List of MaterialType objects ordered by display_order
    """
    query = db.query(MaterialType).filter(MaterialType.active.is_(True))  # noqa: E712
    
    if customer_visible_only:
        query = query.filter(MaterialType.is_customer_visible.is_(True))  # noqa: E712
    
    return query.order_by(MaterialType.display_order).all()


def get_available_colors_for_material(
    db: Session, 
    material_type_code: str,
    in_stock_only: bool = False,
    customer_visible_only: bool = True
) -> List[Color]:
    """
    Get available colors for a specific material type
    
    This is used to populate the color dropdown after material is selected.
    
    Args:
        db: Database session
        material_type_code: Material type code (e.g., 'PLA_BASIC')
        in_stock_only: If True, only return colors that are in stock
        customer_visible_only: If True, only return customer-visible colors
    
    Returns:
        List of Color objects ordered by display_order
    """
    # Get material type
    material = get_material_type(db, material_type_code)
    
    # Build query through junction table
    query = db.query(Color).join(
        MaterialColor,
        and_(
            MaterialColor.color_id == Color.id,
            MaterialColor.material_type_id == material.id,
            MaterialColor.active.is_(True)
        )
    ).filter(
        Color.active.is_(True)
    )
    
    if customer_visible_only:
        query = query.filter(
            Color.is_customer_visible.is_(True),  # noqa: E712
            MaterialColor.is_customer_visible.is_(True)
        )
    
    if in_stock_only:
        # Join to Product and then Inventory to check for available stock
        # Check for both 'material' (new) and 'supply' (legacy) item types
        from sqlalchemy import or_
        query = query.join(
            Product,
            and_(
                Product.material_type_id == material.id,
                Product.color_id == Color.id,
                or_(
                    Product.item_type == 'material',
                    Product.item_type == 'supply'
                ),
                Product.active.is_(True)
            )
        ).join(
            Inventory,
            Inventory.product_id == Product.id
        ).filter(
            Inventory.available_quantity > 0
        )
    
    return query.order_by(Color.display_order, Color.name).all()


def create_material_product(
    db: Session,
    material_type_code: str,
    color_code: str,
    commit: bool = True
) -> Product:
    """
    Creates a 'material' type Product for a given material and color.

    This function is the single source for creating material products, ensuring
    that a corresponding Inventory record is also created.

    UOM Configuration (from centralized config):
    - unit: G (grams) - storage/consumption unit
    - purchase_uom: KG (kilograms) - how vendors sell it
    - purchase_factor: 1000 - conversion factor (1 KG = 1000 G)
    - is_raw_material: True

    Cost is stored per purchase_uom ($/KG), matching vendor pricing.

    Args:
        db: Database session
        material_type_code: The code of the material type (e.g., 'PLA_BASIC')
        color_code: The code of the color (e.g., 'BLK')
        commit: Whether to commit the transaction

    Returns:
        The newly created Product object.
    """
    # Import centralized config
    from app.core.uom_config import DEFAULT_MATERIAL_UOM

    material_type = get_material_type(db, material_type_code)
    color = get_color(db, color_code)

    # Generate SKU from material and color
    sku = f"MAT-{material_type.code}-{color.code}"

    # Check if product already exists
    existing_product = db.query(Product).filter(Product.sku == sku).first()
    if existing_product:
        return existing_product

    # Create the new product with centralized UOM config
    new_product = Product(
        sku=sku,
        name=f"{material_type.name} - {color.name}",
        description=f"Filament material: {material_type.name} in {color.name}",
        item_type='material',  # Use explicit material type
        procurement_type='buy',
        unit=DEFAULT_MATERIAL_UOM.unit,  # G (from config)
        purchase_uom=DEFAULT_MATERIAL_UOM.purchase_uom,  # KG (from config)
        purchase_factor=DEFAULT_MATERIAL_UOM.purchase_factor,  # 1000 (from config) - THIS WAS MISSING!
        standard_cost=material_type.base_price_per_kg,  # Cost is $/KG
        is_raw_material=DEFAULT_MATERIAL_UOM.is_raw_material,  # True (from config)
        material_type_id=material_type.id,
        color_id=color.id,
        active=True
    )
    db.add(new_product)
    db.flush()  # To get the product ID

    # Ensure an inventory record exists for the new product
    # Get default location
    location = db.query(InventoryLocation).filter(InventoryLocation.code == 'MAIN').first()
    if not location:
        # This should ideally not happen if migrations are run
        location = InventoryLocation(name="Main Warehouse", code="MAIN", type="warehouse")
        db.add(location)
        db.flush()

    inventory_record = Inventory(
        product_id=new_product.id,
        location_id=location.id,
        on_hand_quantity=0,
        allocated_quantity=0
    )
    db.add(inventory_record)

    if commit:
        db.commit()

    return new_product


def get_material_product(
    db: Session,
    material_type_code: str,
    color_code: str
) -> Optional[Product]:
    """
    Gets the Product record for a given material and color.

    This is a simple query function. If the product doesn't exist, it returns None.
    Creation is handled by `create_material_product`.

    Args:
        db: Database session
        material_type_code: The code of the material type.
        color_code: The code of the color.

    Returns:
        The Product object if found, otherwise None.
    """
    material_type = get_material_type(db, material_type_code)
    color = get_color(db, color_code)
    sku = f"MAT-{material_type.code}-{color.code}"

    product = db.query(Product).filter(
        Product.sku == sku,
        Product.active.is_(True)
    ).first()

    return product

def get_material_cost_per_kg(
    db: Session,
    material_type_code: str,
    color_code: Optional[str] = None
) -> Decimal:
    """
    Get the cost per kg for a material
    
    If color is specified, returns the specific inventory cost.
    Otherwise returns the base material type cost.
    
    Args:
        db: Database session
        material_type_code: Material type code
        color_code: Optional color code
    
    Returns:
        Cost per kg as Decimal
    """
    material = get_material_type(db, material_type_code)
    
    if color_code:
        product = get_material_product(db, material_type_code, color_code)
        if product and product.standard_cost:
            return product.standard_cost
    
    return material.base_price_per_kg


def get_material_density(db: Session, material_type_code: str) -> Decimal:
    """
    Get the density for a material type
    
    Args:
        db: Database session
        material_type_code: Material type code
    
    Returns:
        Density in g/cm³ as Decimal
    """
    material = get_material_type(db, material_type_code)
    return material.density


def get_material_price_multiplier(db: Session, material_type_code: str) -> Decimal:
    """
    Get the price multiplier for a material type (relative to PLA)
    
    Args:
        db: Database session
        material_type_code: Material type code
    
    Returns:
        Price multiplier as Decimal
    """
    material = get_material_type(db, material_type_code)
    return material.price_multiplier


def check_material_availability(
    db: Session,
    material_type_code: str,
    color_code: str,
    quantity_kg: Decimal
) -> Tuple[bool, str]:
    """
    Check if a material-color combination is available in sufficient quantity
    
    Args:
        db: Database session
        material_type_code: Material type code
        color_code: Color code
        quantity_kg: Required quantity in kg
    
    Returns:
        Tuple of (is_available: bool, message: str)
    """
    product = get_material_product(db, material_type_code, color_code)
    
    if not product:
        return False, f"Material product not found for {material_type_code} + {color_code}"

    # Query inventory for this product
    inventory = db.query(Inventory).filter(
        Inventory.product_id == product.id
    ).first()

    if not inventory:
        return False, f"Inventory record not found for {product.sku}"

    if inventory.available_quantity < quantity_kg:
        return False, (
            f"Insufficient stock: have {inventory.available_quantity}kg, "
            f"need {quantity_kg}kg of {material_type_code} + {color_code}"
        )
    
    return True, "Available"


def get_portal_material_options(db: Session) -> List[dict]:
    """
    Get material options formatted for the portal frontend

    Returns a list of material types with their available colors.
    Includes ALL colors with in_stock status for lead time calculation.

    Returns:
        List of dicts: [
            {
                "code": "PLA_BASIC",
                "name": "PLA Basic",
                "description": "...",
                "price_multiplier": 1.0,
                "colors": [
                    {"code": "BLK", "name": "Black", "hex": "#000000", "in_stock": true},
                    {"code": "WHT", "name": "White", "hex": "#FFFFFF", "in_stock": false},
                    ...
                ]
            },
            ...
        ]
    """
    materials = get_available_material_types(db, customer_visible_only=True)

    result = []
    for material in materials:
        # Get ALL customer-visible colors for this material type
        colors = db.query(Color).join(MaterialColor).filter(
            MaterialColor.material_type_id == material.id,
            Color.is_customer_visible.is_(True),  # noqa: E712
            MaterialColor.is_customer_visible.is_(True),  # noqa: E712
            Color.active.is_(True)
        ).order_by(Color.display_order).all()

        if not colors:
            continue

        # Get all relevant products and their inventory in one go
        color_ids = [c.id for c in colors]
        products_with_inventory = db.query(Product).options(
            joinedload(Product.inventory_items)
        ).filter(
            Product.material_type_id == material.id,
            Product.color_id.in_(color_ids)
        ).all()

        product_map = {p.color_id: p for p in products_with_inventory}

        color_list = []
        for c in colors:
            product = product_map.get(c.id)
            
            # Default to not in stock
            is_in_stock = False
            quantity_kg = 0.0

            if product and product.inventory_items:
                # Sum quantity across all locations
                total_available = sum(inv.available_quantity for inv in product.inventory_items)
                if total_available > 0:
                    is_in_stock = True
                    quantity_kg = float(total_available)

            color_list.append({
                "code": c.code,
                "name": c.name,
                "hex": c.hex_code,
                "hex_secondary": c.hex_code_secondary,
                "in_stock": is_in_stock,
                "quantity_kg": quantity_kg,
            })

        result.append({
            "code": material.code,
            "name": material.name,
            "description": material.description,
            "base_material": material.base_material,
            "price_multiplier": float(material.price_multiplier),
            "strength_rating": material.strength_rating,
            "requires_enclosure": material.requires_enclosure,
            "colors": color_list
        })

    return result


def get_material_product_for_bom(
    db: Session,
    material_type_code: str,
    color_code: str,
    require_in_stock: bool = False
) -> Tuple[Product, Optional[MaterialInventory]]:
    """
    Get or create Product for BOM usage.
    
    This is a compatibility function during the MaterialInventory migration.
    It ensures a Product exists for the given material+color combination and
    returns both the Product and the MaterialInventory (if it exists) for
    backward compatibility.
    
    Eventually, this should be replaced with direct get_material_product() calls
    once MaterialInventory is fully migrated to Products + Inventory.
    
    Args:
        db: Database session
        material_type_code: Material type code (e.g., 'PLA_BASIC')
        color_code: Color code (e.g., 'BLK')
        require_in_stock: If True, raise error if material not in stock
    
    Returns:
        Tuple of (Product, Optional[MaterialInventory])
        - Product: The Product record (always returned)
        - MaterialInventory: The MaterialInventory record if it exists (for backward compat)
    
    Raises:
        MaterialNotFoundError: If material type not found
        ColorNotFoundError: If color not found
        MaterialNotInStockError: If require_in_stock=True and material not in stock
    """
    # Get or create the product
    product = get_material_product(db, material_type_code, color_code)
    
    if not product:
        # Create the product if it doesn't exist
        product = create_material_product(
            db,
            material_type_code=material_type_code,
            color_code=color_code,
            commit=True
        )
    
    # Check stock requirement if needed
    if require_in_stock:
        # Check inventory availability
        inventory = db.query(Inventory).filter(
            Inventory.product_id == product.id
        ).first()
        
        if not inventory or inventory.available_quantity <= 0:
            raise MaterialNotInStockError(
                f"Material not in stock: {material_type_code} + {color_code}"
            )
    
    # For backward compatibility, return MaterialInventory if it exists
    # This allows existing code to continue working during migration
    mat_inv = db.query(MaterialInventory).filter(
        MaterialInventory.material_type_id == product.material_type_id,
        MaterialInventory.color_id == product.color_id,
        MaterialInventory.active.is_(True)
    ).first()
    
    return product, mat_inv


# ---------------------------------------------------------------------------
# Color creation (for a material type)
# ---------------------------------------------------------------------------

def create_color_for_material(
    db: Session,
    material_type_code: str,
    *,
    name: str,
    code: str | None = None,
    hex_code: str | None = None,
) -> tuple[Color, MaterialType]:
    """
    Create a new color and link it to a material type.

    Returns (color, material_type).
    Raises HTTPException on validation errors.
    """
    material_type = db.query(MaterialType).filter(
        MaterialType.code == material_type_code
    ).first()
    if not material_type:
        raise HTTPException(
            status_code=404, detail=f"Material type not found: {material_type_code}"
        )

    # Generate code if not provided
    color_code = code
    if not color_code:
        color_code = name.upper().replace(" ", "_").replace("-", "_")
        base_code = color_code
        counter = 1
        while db.query(Color).filter(Color.code == color_code).first():
            color_code = f"{base_code}_{counter}"
            counter += 1

    existing_color = db.query(Color).filter(Color.code == color_code).first()

    if existing_color:
        color = existing_color
        existing_link = db.query(MaterialColor).filter(
            MaterialColor.material_type_id == material_type.id,
            MaterialColor.color_id == color.id,
        ).first()
        if existing_link:
            raise HTTPException(
                status_code=400,
                detail=f"Color '{color.name}' is already linked to {material_type.name}",
            )
    else:
        color = Color(
            code=color_code,
            name=name,
            hex_code=hex_code,
            active=True,
            is_customer_visible=True,
            display_order=100,
        )
        db.add(color)
        db.flush()

    material_color = MaterialColor(
        material_type_id=material_type.id,
        color_id=color.id,
        is_customer_visible=True,
        active=True,
    )
    db.add(material_color)
    db.commit()
    db.refresh(color)

    return color, material_type


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

# Base-material inference from material type code
_BASE_MATERIAL_MAP = {
    "PETG": "PETG",
    "ABS": "ABS",
    "ASA": "ASA",
    "TPU": "TPU",
    "PAHT": "PAHT",
    "PC": "PC",
}


def _infer_base_material(material_type_code: str) -> str:
    """Infer base material from a material type code."""
    for key, value in _BASE_MATERIAL_MAP.items():
        if key in material_type_code:
            return value
    return "PLA"


# Column name variations for CSV parsing
_SKU_COLS = ["sku", "SKU", "Sku"]
_NAME_COLS = ["name", "Name", "Product Name"]
_CATEGORY_COLS = ["category", "Category", "CATEGORY", "Category Name"]
_MATERIAL_TYPE_COLS = [
    "material type", "Material Type", "material_type", "Material_Type",
]
_COLOR_NAME_COLS = [
    "material color name", "Material Color Name", "material_color_name",
    "Color Name", "color name",
]
_HEX_COLS = ["hex code", "HEX Code", "hex_code", "HEX", "hex"]
_PRICE_COLS = ["price", "Price", "PRICE"]
_ON_HAND_COLS = [
    "on hand (g)", "On Hand (g)", "on_hand_g", "On Hand", "on hand",
    "quantity", "Quantity",
]


def _get_column_value(
    row: dict, possible_names: list[str], normalized_map: dict[str, str]
) -> str:
    """Get value from CSV row using case-insensitive column name matching."""
    for name in possible_names:
        if name in row and row[name] and row[name].strip():
            return row[name].strip()
        lower_name = name.lower()
        if lower_name in normalized_map:
            original_name = normalized_map[lower_name]
            if original_name in row and row[original_name] and row[original_name].strip():
                return row[original_name].strip()
    return ""


def import_materials_from_csv(
    db: Session,
    *,
    file_content: bytes,
    update_existing: bool = False,
    import_categories: bool = True,
) -> dict:
    """
    Import material inventory from CSV file content.

    Returns dict with keys: total_rows, created, updated, skipped, errors.
    """
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    if text.startswith("\ufeff"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))

    fieldnames = reader.fieldnames or []
    normalized_map: dict[str, str] = {}
    for fn in fieldnames:
        clean = fn.strip() if fn else ""
        normalized_map[clean.lower()] = fn

    result = {
        "total_rows": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }

    # Default inventory location
    default_location = db.query(InventoryLocation).filter(
        InventoryLocation.code == "MAIN"
    ).first()
    if not default_location:
        default_location = InventoryLocation(
            code="MAIN", name="Main Warehouse", type="warehouse", active=True,
        )
        db.add(default_location)
        db.commit()
        db.refresh(default_location)

    # Filament root category
    filament_root_category = None
    if import_categories:
        filament_root_category = db.query(ItemCategory).filter(
            ItemCategory.code == "FILAMENT"
        ).first()
        if not filament_root_category:
            filament_root_category = ItemCategory(
                code="FILAMENT",
                name="Filament",
                description="Filament materials for 3D printing",
                sort_order=0,
                is_active=True,
            )
            db.add(filament_root_category)
            db.flush()

    for row_num, row in enumerate(reader, start=2):
        result["total_rows"] += 1
        sku = ""

        try:
            sku = _get_column_value(row, _SKU_COLS, normalized_map)
            if not sku:
                result["errors"].append(
                    {"row": row_num, "error": "SKU is required", "sku": ""}
                )
                result["skipped"] += 1
                continue

            material_type_code = _get_column_value(
                row, _MATERIAL_TYPE_COLS, normalized_map
            ).upper()
            if not material_type_code:
                result["errors"].append(
                    {"row": row_num, "error": "Material Type is required", "sku": sku}
                )
                result["skipped"] += 1
                continue

            color_name = _get_column_value(row, _COLOR_NAME_COLS, normalized_map)
            if not color_name:
                result["errors"].append(
                    {"row": row_num, "error": "Material Color Name is required", "sku": sku}
                )
                result["skipped"] += 1
                continue

            hex_code = _get_column_value(row, _HEX_COLS, normalized_map)

            price: Decimal | None = None
            price_str = _get_column_value(row, _PRICE_COLS, normalized_map)
            if price_str:
                try:
                    price = Decimal(price_str.replace("$", "").replace(",", ""))
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse price '{price_str}': {e}")

            on_hand_kg = Decimal("0.00")
            on_hand_str = _get_column_value(row, _ON_HAND_COLS, normalized_map)
            if on_hand_str:
                try:
                    grams = Decimal(on_hand_str.replace(",", ""))
                    on_hand_kg = grams / Decimal("1000")
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse on_hand quantity '{on_hand_str}': {e}")

            # Category handling
            category_id = None
            if import_categories and filament_root_category:
                category_name = _get_column_value(row, _CATEGORY_COLS, normalized_map)
                if category_name:
                    category_code = (
                        category_name.upper().replace(" ", "_").replace("-", "_")[:50]
                    )
                    subcategory = db.query(ItemCategory).filter(
                        ItemCategory.code == category_code,
                        ItemCategory.parent_id == filament_root_category.id,
                    ).first()
                    if not subcategory:
                        subcategory = ItemCategory(
                            code=category_code,
                            name=category_name,
                            parent_id=filament_root_category.id,
                            description=f"Filament category: {category_name}",
                            sort_order=0,
                            is_active=True,
                        )
                        db.add(subcategory)
                        db.flush()
                    category_id = subcategory.id

            # Get or create material type
            material_type = db.query(MaterialType).filter(
                MaterialType.code == material_type_code
            ).first()
            if not material_type:
                base_material = _infer_base_material(material_type_code)
                material_type = MaterialType(
                    code=material_type_code,
                    name=material_type_code.replace("_", " ").title(),
                    base_material=base_material,
                    density=Decimal("1.24"),
                    base_price_per_kg=price or Decimal("20.00"),
                    price_multiplier=Decimal("1.0"),
                    active=True,
                    is_customer_visible=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(material_type)
                db.flush()

            # Get or create color
            color_code_gen = color_name.upper().replace(" ", "_").replace("-", "_")[:30]
            color = db.query(Color).filter(Color.code == color_code_gen).first()
            if not color:
                color = Color(
                    code=color_code_gen,
                    name=color_name,
                    hex_code=hex_code or None,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(color)
                db.flush()
            elif hex_code and not color.hex_code:
                color.hex_code = hex_code
                color.updated_at = datetime.now(timezone.utc)

            # MaterialColor link
            material_color = db.query(MaterialColor).filter(
                MaterialColor.material_type_id == material_type.id,
                MaterialColor.color_id == color.id,
            ).first()
            if not material_color:
                material_color = MaterialColor(
                    material_type_id=material_type.id,
                    color_id=color.id,
                    active=True,
                )
                db.add(material_color)

            # Get or create product
            product = db.query(Product).filter(Product.sku == sku).first()
            if product:
                if not update_existing:
                    result["skipped"] += 1
                    continue
                result["updated"] += 1
            else:
                name = ""
                for col in _NAME_COLS:
                    if row.get(col, "").strip():
                        name = row.get(col, "").strip()
                        break
                if not name:
                    name = f"{material_type.name} - {color_name}"

                from app.core.uom_config import DEFAULT_MATERIAL_UOM

                product = Product(
                    sku=sku,
                    name=name,
                    description=f"Filament supply: {material_type.name} in {color_name}",
                    item_type="supply",
                    procurement_type="buy",
                    unit=DEFAULT_MATERIAL_UOM.unit,
                    purchase_uom=DEFAULT_MATERIAL_UOM.purchase_uom,
                    purchase_factor=DEFAULT_MATERIAL_UOM.purchase_factor,
                    is_raw_material=DEFAULT_MATERIAL_UOM.is_raw_material,
                    standard_cost=float(price) if price else float(material_type.base_price_per_kg),
                    material_type_id=material_type.id,
                    color_id=color.id,
                    category_id=category_id,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(product)
                db.flush()
                result["created"] += 1

            if price and product.standard_cost != float(price):
                product.standard_cost = float(price)
                product.updated_at = datetime.now(timezone.utc)

            if import_categories and category_id and product.category_id != category_id:
                product.category_id = category_id
                product.updated_at = datetime.now(timezone.utc)

            # Inventory record
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product.id,
                Inventory.location_id == default_location.id,
            ).first()
            if not inventory:
                inventory = Inventory(
                    product_id=product.id,
                    location_id=default_location.id,
                    on_hand_quantity=on_hand_kg,
                    allocated_quantity=Decimal("0.00"),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(inventory)
            else:
                inventory.on_hand_quantity = on_hand_kg
                inventory.updated_at = datetime.now(timezone.utc)

            try:
                db.commit()
            except Exception as commit_err:
                db.rollback()
                result["errors"].append(
                    {"row": row_num, "error": f"Database error: {str(commit_err)}", "sku": sku}
                )
                result["skipped"] += 1
                continue

        except Exception as e:
            db.rollback()
            sku_value = sku if sku else ""
            result["errors"].append(
                {"row": row_num, "error": str(e), "sku": sku_value}
            )
            result["skipped"] += 1

    return result
