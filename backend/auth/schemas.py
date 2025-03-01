# backend/auth/schemas.py
from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    username: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    username: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None


class TokenPayload(schemas.BaseModel):
    token: str
