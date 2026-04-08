from typing import Optional

import httpx

from app.core.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class NotificationDispatchClient:
    @property
    def base_url(self) -> str | None:
        if not settings.NOTIFICATION_SERVICE_URL:
            return None
        return settings.NOTIFICATION_SERVICE_URL.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and settings.NOTIFICATION_SERVICE_TOKEN)

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> Optional[bool]:
        if not self.is_configured:
            return None

        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/notifications/email",
                json={
                    "to_email": to_email,
                    "subject": subject,
                    "html_body": html_body,
                    "text_body": text_body,
                },
                headers={
                    "Authorization": f"Bearer {settings.NOTIFICATION_SERVICE_TOKEN}",
                },
                timeout=settings.NOTIFICATION_SERVICE_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            logger.error("Notification service request failed: %s", exc)
            return False

        if not response.is_success:
            logger.error(
                "Notification service returned %s while delivering to %s",
                response.status_code,
                to_email,
            )
            return False

        try:
            payload = response.json()
        except ValueError:
            logger.error("Notification service returned invalid JSON for %s", to_email)
            return False

        delivered = bool(payload.get("delivered"))
        if delivered:
            logger.info("Notification service delivered email to %s", to_email)
        else:
            logger.warning("Notification service accepted but did not deliver email to %s", to_email)
        return delivered


notification_dispatch_client = NotificationDispatchClient()
