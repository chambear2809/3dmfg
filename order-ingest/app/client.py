import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


def enrich_with_pricing(skus: list[str]) -> dict[str, dict] | None:
    """Call the pricing service to get cost estimates for the given SKUs.

    Returns a mapping of SKU -> pricing data, or None if the service is
    unavailable or unconfigured.  Failures are logged but never raised so
    that CSV parsing succeeds regardless of pricing-service health.
    """
    base_url = settings.PRICING_SERVICE_URL
    token = settings.PRICING_SERVICE_TOKEN

    if not base_url or not token:
        return None

    url = f"{base_url.rstrip('/')}/api/v1/pricing/validate"
    try:
        response = httpx.post(
            url,
            json={"skus": skus},
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.PRICING_SERVICE_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        logger.warning("Pricing service request failed: %s", exc)
        return None

    if not response.is_success:
        logger.warning("Pricing service returned %s", response.status_code)
        return None

    try:
        data = response.json()
    except ValueError:
        logger.warning("Pricing service returned invalid JSON")
        return None

    return {
        item["sku"]: item
        for item in data.get("items", [])
    }
