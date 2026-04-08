import logging
import uuid

from fastapi import APIRouter, Depends, FastAPI, Request

from .auth import require_internal_token
from .config import settings
from .delivery import delivery_service
from .models import (
    DeliveryResponse,
    EmailNotificationRequest,
    HealthResponse,
    RootResponse,
    WebhookNotificationRequest,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/", response_model=RootResponse)
async def root():
    return RootResponse(
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        status="ok",
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        status="ok",
        smtp_configured=settings.smtp_configured,
    )


@router.post("/email", response_model=DeliveryResponse, dependencies=[Depends(require_internal_token)])
async def send_email(payload: EmailNotificationRequest):
    return delivery_service.send_email(payload)


@router.post("/webhook", response_model=DeliveryResponse, dependencies=[Depends(require_internal_token)])
async def send_webhook(payload: WebhookNotificationRequest):
    return delivery_service.send_webhook(payload)


app.include_router(router)
