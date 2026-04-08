from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class RootResponse(BaseModel):
    service: str
    version: str
    status: str


class HealthResponse(RootResponse):
    smtp_configured: bool


class DeliveryResponse(BaseModel):
    accepted: bool = True
    delivered: bool
    provider: str
    detail: str
    status_code: int | None = None


class EmailNotificationRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    html_body: str = Field(min_length=1)
    text_body: str | None = None


class WebhookNotificationRequest(BaseModel):
    url: HttpUrl
    method: Literal["POST", "PUT", "PATCH"] = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    json_body: dict[str, Any] | list[Any] | None = None
    timeout_seconds: float | None = Field(default=None, gt=0.0, le=30.0)
