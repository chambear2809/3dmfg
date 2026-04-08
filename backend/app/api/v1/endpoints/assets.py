from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.services.asset_dispatch_client import (
    AssetServiceClientError,
    AssetServiceNotFoundError,
    asset_dispatch_client,
)

router = APIRouter(prefix="/assets", tags=["Assets"])

_LOCAL_PRODUCT_IMAGE_DIR = (
    Path(__file__).parent.parent.parent.parent / "static" / "uploads" / "products"
)


@router.get("/product-images/{asset_key}")
async def get_product_image(asset_key: str):
    safe_asset_key = Path(asset_key).name
    if safe_asset_key != asset_key:
        raise HTTPException(status_code=400, detail="Invalid asset key")

    if asset_dispatch_client.is_configured:
        try:
            asset = asset_dispatch_client.fetch(
                category="product-images",
                asset_key=safe_asset_key,
            )
        except AssetServiceNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Asset not found") from exc
        except AssetServiceClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return Response(
            content=asset["content"],
            media_type=asset["content_type"],
            headers={
                "Content-Disposition": f'inline; filename="{asset["filename"]}"',
            },
        )

    local_path = _LOCAL_PRODUCT_IMAGE_DIR / safe_asset_key
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    return FileResponse(local_path)
