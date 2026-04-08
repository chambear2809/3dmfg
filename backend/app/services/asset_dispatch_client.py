import httpx

from app.core.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class AssetServiceClientError(RuntimeError):
    """Raised when the asset service returns an error."""


class AssetServiceNotFoundError(AssetServiceClientError):
    """Raised when the requested asset does not exist."""


class AssetDispatchClient:
    @property
    def base_url(self) -> str | None:
        if not settings.ASSET_SERVICE_URL:
            return None
        return settings.ASSET_SERVICE_URL.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and settings.ASSET_SERVICE_TOKEN)

    def upload(
        self,
        *,
        category: str,
        filename: str,
        content: bytes,
        content_type: str,
        asset_key: str | None = None,
    ) -> dict | None:
        if not self.is_configured:
            return None

        try:
            data = {"category": category}
            if asset_key is not None:
                data["asset_key"] = asset_key

            response = httpx.post(
                f"{self.base_url}/api/v1/assets/upload",
                data=data,
                files={
                    "file": (filename, content, content_type),
                },
                headers={
                    "Authorization": f"Bearer {settings.ASSET_SERVICE_TOKEN}",
                },
                timeout=settings.ASSET_SERVICE_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            logger.error("Asset service upload failed: %s", exc)
            raise AssetServiceClientError("Asset service upload failed") from exc

        if not response.is_success:
            logger.error("Asset service upload returned %s", response.status_code)
            raise AssetServiceClientError("Asset service upload failed")

        return response.json()

    def fetch(self, *, category: str, asset_key: str) -> dict | None:
        if not self.is_configured:
            return None

        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/assets/{category}/{asset_key}",
                headers={
                    "Authorization": f"Bearer {settings.ASSET_SERVICE_TOKEN}",
                },
                timeout=settings.ASSET_SERVICE_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            logger.error("Asset service fetch failed: %s", exc)
            raise AssetServiceClientError("Asset service fetch failed") from exc

        if response.status_code == 404:
            raise AssetServiceNotFoundError("Asset not found")

        if not response.is_success:
            logger.error("Asset service fetch returned %s", response.status_code)
            raise AssetServiceClientError("Asset service fetch failed")

        return {
            "content": response.content,
            "content_type": response.headers.get("content-type", "application/octet-stream"),
            "filename": response.headers.get("x-asset-filename") or asset_key,
        }

    def delete(self, *, category: str, asset_key: str) -> bool | None:
        if not self.is_configured:
            return None

        try:
            response = httpx.delete(
                f"{self.base_url}/api/v1/assets/{category}/{asset_key}",
                headers={
                    "Authorization": f"Bearer {settings.ASSET_SERVICE_TOKEN}",
                },
                timeout=settings.ASSET_SERVICE_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            logger.error("Asset service delete failed: %s", exc)
            raise AssetServiceClientError("Asset service delete failed") from exc

        if response.status_code == 404:
            raise AssetServiceNotFoundError("Asset not found")

        if not response.is_success:
            logger.error("Asset service delete returned %s", response.status_code)
            raise AssetServiceClientError("Asset service delete failed")

        payload = response.json()
        return bool(payload.get("deleted"))


asset_dispatch_client = AssetDispatchClient()
