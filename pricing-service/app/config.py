from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_PRODUCTION_ENVIRONMENTS = {"production", "3dprint"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "FilaOps Pricing Service"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    INTERNAL_API_TOKEN: str = Field(
        default="change-me-pricing-token",
        description="Bearer token required for internal callers.",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in _PRODUCTION_ENVIRONMENTS

    @model_validator(mode="after")
    def validate_production_token(self):
        if self.is_production and self.INTERNAL_API_TOKEN == "change-me-pricing-token":
            raise ValueError("Set a real INTERNAL_API_TOKEN before running in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
