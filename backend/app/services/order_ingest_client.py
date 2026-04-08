import httpx

from app.core.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class OrderIngestServiceClientError(RuntimeError):
    """Raised when the order ingest service returns an error."""


class OrderIngestClient:
    @property
    def base_url(self) -> str | None:
        if not settings.ORDER_INGEST_SERVICE_URL:
            return None
        return settings.ORDER_INGEST_SERVICE_URL.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and settings.ORDER_INGEST_SERVICE_TOKEN)

    def parse_csv(self, *, csv_text: str) -> dict | None:
        if not self.is_configured:
            return None

        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/order-ingest/parse-csv",
                json={"csv_text": csv_text},
                headers={
                    "Authorization": f"Bearer {settings.ORDER_INGEST_SERVICE_TOKEN}",
                },
                timeout=settings.ORDER_INGEST_SERVICE_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            logger.error("Order ingest service request failed: %s", exc)
            raise OrderIngestServiceClientError("Order ingest service request failed") from exc

        if not response.is_success:
            logger.error("Order ingest service returned %s", response.status_code)
            raise OrderIngestServiceClientError("Order ingest service request failed")

        return response.json()


order_ingest_client = OrderIngestClient()
