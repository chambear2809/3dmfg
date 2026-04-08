import logging
import uuid

from fastapi import APIRouter, Depends, FastAPI, Request

from .auth import require_internal_token
from .client import enrich_with_pricing
from .config import settings
from .models import HealthResponse, ParseCsvRequest, ParseCsvResponse, RootResponse
from .parser import parse_orders_from_csv

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

router = APIRouter(prefix="/api/v1/order-ingest", tags=["Order Ingest"])


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
        parser_ready=True,
    )


@router.post("/parse-csv", response_model=ParseCsvResponse, dependencies=[Depends(require_internal_token)])
async def parse_csv(request: ParseCsvRequest):
    result = parse_orders_from_csv(request.csv_text)

    all_skus = list({line.sku for order in result.orders for line in order.lines})
    if all_skus:
        pricing = enrich_with_pricing(all_skus)
        if pricing:
            for order in result.orders:
                for line in order.lines:
                    item = pricing.get(line.sku)
                    if item and line.unit_price is None:
                        line.unit_price = item.get("unit_cost")

    return result


app.include_router(router)
