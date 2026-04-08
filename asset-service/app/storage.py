import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import settings

_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


class AssetStorageService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _sanitize_segment(self, value: str) -> str:
        normalized = _SAFE_SEGMENT_RE.sub("-", value.strip())
        normalized = normalized.strip(".-")
        if not normalized:
            raise ValueError("Asset path segment cannot be empty")
        return normalized

    def _asset_dir(self, category: str) -> Path:
        safe_category = self._sanitize_segment(category)
        path = self.root / safe_category
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _asset_path(self, category: str, asset_key: str) -> Path:
        safe_key = self._sanitize_segment(asset_key)
        return self._asset_dir(category) / safe_key

    def _metadata_path(self, category: str, asset_key: str) -> Path:
        safe_key = self._sanitize_segment(asset_key)
        return self._asset_dir(category) / f"{safe_key}.meta.json"

    def save_asset(
        self,
        *,
        category: str,
        content: bytes,
        filename: str,
        content_type: str | None,
        asset_key: str | None = None,
    ) -> dict:
        suffix = Path(filename or "").suffix.lower()
        resolved_key = asset_key or f"{uuid4().hex}{suffix}"
        safe_key = self._sanitize_segment(resolved_key)
        safe_category = self._sanitize_segment(category)

        asset_path = self._asset_path(safe_category, safe_key)
        metadata_path = self._metadata_path(safe_category, safe_key)

        resolved_content_type = (
            content_type
            or mimetypes.guess_type(filename or safe_key)[0]
            or "application/octet-stream"
        )

        asset_path.write_bytes(content)
        metadata_path.write_text(
            json.dumps(
                {
                    "filename": filename or safe_key,
                    "content_type": resolved_content_type,
                    "size": len(content),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )

        return {
            "category": safe_category,
            "asset_key": safe_key,
            "filename": filename or safe_key,
            "content_type": resolved_content_type,
            "size": len(content),
        }

    def get_asset(self, *, category: str, asset_key: str) -> dict | None:
        safe_category = self._sanitize_segment(category)
        safe_key = self._sanitize_segment(asset_key)
        asset_path = self._asset_path(safe_category, safe_key)
        metadata_path = self._metadata_path(safe_category, safe_key)

        if not asset_path.exists():
            return None

        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}

        content_type = (
            metadata.get("content_type")
            or mimetypes.guess_type(asset_path.name)[0]
            or "application/octet-stream"
        )

        return {
            "category": safe_category,
            "asset_key": safe_key,
            "filename": metadata.get("filename") or asset_path.name,
            "content_type": content_type,
            "content": asset_path.read_bytes(),
        }

    def delete_asset(self, *, category: str, asset_key: str) -> bool:
        safe_category = self._sanitize_segment(category)
        safe_key = self._sanitize_segment(asset_key)
        asset_path = self._asset_path(safe_category, safe_key)
        metadata_path = self._metadata_path(safe_category, safe_key)

        existed = False
        if asset_path.exists():
            asset_path.unlink()
            existed = True
        if metadata_path.exists():
            metadata_path.unlink()
            existed = True
        return existed


asset_storage = AssetStorageService()
