from decimal import Decimal

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    service: str
    version: str
    status: str


class HealthResponse(RootResponse):
    engine_ready: bool = True


class PricingItem(BaseModel):
    sku: str
    unit_cost: Decimal = Field(ge=0)
    currency: str = "USD"
    available: bool = True


class PricingRequest(BaseModel):
    skus: list[str] = Field(min_length=1)


class PricingResponse(BaseModel):
    items: list[PricingItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
