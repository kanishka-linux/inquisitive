# backend/auth/service.py
from datetime import datetime
from jose import jwt

from backend.config import settings
from backend.core.logging import get_logger

# import logging

logger = get_logger()


def validate_jwt_token(token: str) -> dict:
    """Validate a JWT token and return user info if valid"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_TOKEN_AUDIENCE
        )

        user_id = payload.get("sub")
        if user_id is None:
            return {"valid": False}

        # Check token expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcnow() > datetime.fromtimestamp(exp):
            return {"valid": False}

        return {
            "valid": True,
            "user_id": user_id
        }
    except Exception as e:
        print(f"Token validation error: {e}")
        return {"valid": False}
