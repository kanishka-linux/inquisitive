# backend/auth/schemas.py
from typing import Optional
from fastapi_users import schemas
from datetime import datetime


class UserRead(schemas.BaseUser[int]):
    username: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    username: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None


class TokenPayload(schemas.BaseModel):
    token: str


class FileUploadResponse(schemas.BaseModel):
    filename: str
    file_url: str
    upload_time: datetime

    class Config:
        from_attrributes = True


class FileUploadDB(schemas.BaseModel):
    id: int
    filename: str
    original_filename: str
    file_path: str
    file_url: str
    content_type: str
    upload_time: datetime
    user_id: int

    class Config:
        from_attrributes = True
