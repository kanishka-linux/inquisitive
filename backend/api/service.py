# backend/auth/service.py
from datetime import datetime
from jose import jwt

from backend.config import settings
from backend.core.logging import get_logger
import uuid
import os

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


def save_file(content, title):
    # Generate a unique ID
    doc_id = str(uuid.uuid4())

    # Create a filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if title:
        # Replace spaces with underscores and remove special characters
        safe_title = ''.join(c if c.isalnum() else '-' for c in title)
        filename = f"{safe_title}-{timestamp}.md"
    else:
        filename = f"{doc_id}_{timestamp}.md"

    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Write content to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return doc_id, file_path, filename
