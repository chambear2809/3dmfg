import asyncio
import hashlib
from decimal import Decimal

from .models import PricingItem


async def compute_pricing(skus: list[str]) -> list[PricingItem]:
    """Return deterministic cost estimates for the given SKUs.

    Uses a hash-based stub so the same SKU always produces the same price,
    making the service map demo reproducible while still exercising a
    realistic request/response cycle with processing latency.
    """
    await asyncio.sleep(0.015)

    items: list[PricingItem] = []
    for sku in skus:
        digest = hashlib.sha256(sku.encode()).hexdigest()
        cents = int(digest[:6], 16) % 50000 + 100
        items.append(
            PricingItem(
                sku=sku,
                unit_cost=Decimal(cents) / Decimal(100),
                currency="USD",
                available=int(digest[6:8], 16) % 10 > 1,
            )
        )
    return items
