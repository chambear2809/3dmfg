import logging
import uuid

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile

from .auth import require_internal_token
from .config import settings
from .models import AssetDeleteResponse, AssetUploadResponse, HealthResponse, RootResponse
from .storage import asset_storage

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])


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
        storage_dir=str(settings.storage_dir),
    )


@router.post("/upload", response_model=AssetUploadResponse, dependencies=[Depends(require_internal_token)])
async def upload_asset(
    category: str = Form(...),
    asset_key: str | None = Form(default=None),
    file: UploadFile = File(...),
):
    content = await file.read()
    result = asset_storage.save_asset(
        category=category,
        content=content,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        asset_key=asset_key,
    )
    return AssetUploadResponse(
        **result,
        url_path=f"/api/v1/assets/{result['category']}/{result['asset_key']}",
    )


@router.get("/{category}/{asset_key}", dependencies=[Depends(require_internal_token)])
async def get_asset(category: str, asset_key: str):
    asset = asset_storage.get_asset(category=category, asset_key=asset_key)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return Response(
        content=asset["content"],
        media_type=asset["content_type"],
        headers={"X-Asset-Filename": asset["filename"]},
    )


@router.delete(
    "/{category}/{asset_key}",
    response_model=AssetDeleteResponse,
    dependencies=[Depends(require_internal_token)],
)
async def delete_asset(category: str, asset_key: str):
    deleted = asset_storage.delete_asset(category=category, asset_key=asset_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")

    return AssetDeleteResponse(
        deleted=True,
        category=category,
        asset_key=asset_key,
    )


app.include_router(router)
