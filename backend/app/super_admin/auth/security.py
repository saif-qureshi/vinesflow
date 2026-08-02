from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings

ACCESS_TOKEN_TYPE = "super_admin_access"


def create_access_token(subject: str | int) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
