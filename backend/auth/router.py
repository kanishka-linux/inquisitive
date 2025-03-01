# backend/auth/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import (
    auth_backend,
    current_active_user,
    fastapi_users,
)
from backend.auth.models import User
from backend.auth.schemas import TokenPayload, UserCreate, UserRead, UserUpdate
from backend.auth.service import validate_jwt_token
from backend.database import get_async_session
from backend.core.logging import get_logger

# import logging

logger = get_logger()


router = APIRouter()

# Include FastAPI Users routers
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Custom token validation endpoint


@router.post("/validate-token", tags=["auth"])
async def validate_token(payload: TokenPayload):
    """Validate a JWT token and return user info if valid"""
    logger.info("-----validating----------")
    return validate_jwt_token(payload.token)

# Custom endpoint to get user by username


@router.get("/users/by-username/{username}", response_model=UserRead, tags=["users"])
async def get_user_by_username(
    username: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a user by username"""
    query = select(User).where(User.username == username)
    result = await session.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

# Protected endpoint example


@router.get("/protected-resource", tags=["auth"])
async def protected_resource(user: User = Depends(current_active_user)):
    """Example of a protected resource that requires authentication"""
    return {
        "message": "This is a protected resource",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }
