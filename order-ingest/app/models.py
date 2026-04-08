from decimal import Decimal

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    service: str
    version: str
    status: str


class HealthResponse(RootResponse):
    parser_ready: bool = True


class ParseError(BaseModel):
    row: int | None = None
    order_id: str | None = None
    error: str


class NormalizedOrderLine(BaseModel):
    sku: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1)
    unit_price: Decimal | None = Field(default=None, ge=0)


class NormalizedOrder(BaseModel):
    source_order_id: str = Field(min_length=1, max_length=255)
    customer_email: str = Field(min_length=1, max_length=255)
    customer_name: str | None = Field(default=None, max_length=255)
    shipping_address: dict[str, str] = Field(default_factory=dict)
    shipping_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    lines: list[NormalizedOrderLine] = Field(default_factory=list)


class ParseCsvRequest(BaseModel):
    csv_text: str = Field(min_length=1)


class ParseCsvResponse(BaseModel):
    total_rows: int = Field(ge=0)
    orders: list[NormalizedOrder] = Field(default_factory=list)
    errors: list[ParseError] = Field(default_factory=list)
