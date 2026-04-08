import logging
import uuid

from fastapi import APIRouter, Depends, FastAPI, Request

from .auth import require_internal_token
from .config import settings
from .models import HealthResponse, PricingRequest, PricingResponse, RootResponse
from .pricing import compute_pricing

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    if not getattr(app, "_is_instrumented_by_opentelemetry", False):
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
except Exception:
    pass

router = APIRouter(prefix="/api/v1/pricing", tags=["Pricing"])


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
        engine_ready=True,
    )


@router.post("/validate", response_model=PricingResponse, dependencies=[Depends(require_internal_token)])
async def validate_pricing(request: PricingRequest):
    items = await compute_pricing(request.skus)
    return PricingResponse(items=items)


app.include_router(router)
