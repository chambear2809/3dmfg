import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from .config import settings
from .models import (
    DeliveryResponse,
    EmailNotificationRequest,
    WebhookNotificationRequest,
)

logger = logging.getLogger(__name__)


class NotificationDeliveryService:
    def send_email(self, payload: EmailNotificationRequest) -> DeliveryResponse:
        if not settings.smtp_configured:
            logger.warning("SMTP credentials not configured; skipping email to %s", payload.to_email)
            return DeliveryResponse(
                accepted=True,
                delivered=False,
                provider="smtp",
                detail="SMTP credentials are not configured",
            )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = payload.subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = payload.to_email

        if payload.text_body:
            msg.attach(MIMEText(payload.text_body, "plain"))
        msg.attach(MIMEText(payload.html_body, "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, payload.to_email, msg.as_string())
        except Exception as exc:
            logger.exception("Failed to deliver email to %s", payload.to_email)
            return DeliveryResponse(
                accepted=True,
                delivered=False,
                provider="smtp",
                detail=str(exc),
            )

        logger.info("Delivered email to %s", payload.to_email)
        return DeliveryResponse(
            accepted=True,
            delivered=True,
            provider="smtp",
            detail="Email delivered successfully",
        )

    def send_webhook(self, payload: WebhookNotificationRequest) -> DeliveryResponse:
        timeout = payload.timeout_seconds or settings.DEFAULT_WEBHOOK_TIMEOUT_SECONDS
        request_kwargs: dict[str, object] = {"headers": payload.headers}
        if payload.json_body is not None:
            request_kwargs["json"] = payload.json_body

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(payload.method, str(payload.url), **request_kwargs)
        except Exception as exc:
            logger.exception("Failed to deliver webhook to %s", payload.url)
            return DeliveryResponse(
                accepted=True,
                delivered=False,
                provider="webhook",
                detail=str(exc),
            )

        delivered = response.is_success
        if delivered:
            logger.info("Delivered webhook to %s with status %s", payload.url, response.status_code)
        else:
            logger.warning("Webhook delivery to %s returned status %s", payload.url, response.status_code)

        return DeliveryResponse(
            accepted=True,
            delivered=delivered,
            provider="webhook",
            detail="Webhook delivered" if delivered else response.text[:200],
            status_code=response.status_code,
        )


delivery_service = NotificationDeliveryService()
