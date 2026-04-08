import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


def notify_asset_event(*, category: str, asset_key: str, filename: str, action: str) -> None:
    """Send an email notification about an asset event.

    Failures are logged but never raised so the upload/delete response is
    not blocked by notification-service availability.
    """
    base_url = settings.NOTIFICATION_SERVICE_URL
    token = settings.NOTIFICATION_SERVICE_TOKEN

    if not base_url or not token:
        return

    url = f"{base_url.rstrip('/')}/api/v1/notifications/email"
    try:
        httpx.post(
            url,
            json={
                "to_email": "assets@filaops.local",
                "subject": f"Asset {action}: {filename}",
                "html_body": (
                    f"<p>Asset event: <strong>{action}</strong></p>"
                    f"<p>Category: {category}<br>Key: {asset_key}<br>File: {filename}</p>"
                ),
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.NOTIFICATION_SERVICE_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        logger.warning("Notification service request failed: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error notifying asset event: %s", exc)
