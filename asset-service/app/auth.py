import hmac

from fastapi import Header, HTTPException, status

from .config import settings


def require_internal_token(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
) -> None:
    token = x_internal_token

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token or not hmac.compare_digest(token, settings.INTERNAL_API_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid asset service token",
        )
