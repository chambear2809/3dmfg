"""
Helpers for explicit demo-only bootstrap behavior.
"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.logging_config import get_logger
from app.models.user import User

logger = get_logger(__name__)


def bootstrap_demo_admin(db: Session) -> User | None:
    """Create the first admin user from DEMO_ADMIN_* settings when enabled."""
    if not settings.DEMO_ADMIN_ENABLED:
        return None

    if db.query(User).count() > 0:
        return None

    name_parts = settings.DEMO_ADMIN_FULL_NAME.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    admin = User(
        email=str(settings.DEMO_ADMIN_EMAIL),
        password_hash=hash_password(settings.DEMO_ADMIN_PASSWORD or ""),
        first_name=first_name,
        last_name=last_name,
        company_name=settings.DEMO_ADMIN_COMPANY_NAME or None,
        account_type="admin",
        status="active",
        email_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    logger.warning(
        "Demo admin bootstrapped from environment",
        extra={"email": admin.email, "account_type": admin.account_type},
    )
    return admin
