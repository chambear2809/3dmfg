from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    service: str
    version: str
    status: str


class HealthResponse(RootResponse):
    storage_dir: str


class AssetUploadResponse(BaseModel):
    category: str
    asset_key: str
    filename: str
    content_type: str
    size: int = Field(ge=0)
    url_path: str


class AssetDeleteResponse(BaseModel):
    deleted: bool
    category: str
    asset_key: str
