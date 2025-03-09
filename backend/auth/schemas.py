# backend/auth/schemas.py
from typing import Optional, List, Dict
from fastapi_users import schemas
from datetime import datetime
from pydantic import HttpUrl, Field
from backend.config import settings


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
        from_attributes = True


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
        from_attributes = True


class LinkBase(schemas.BaseModel):
    url: HttpUrl
    headers: Optional[Dict[str, str]] = Field(
        default=settings.DEFAULT_HEADERS, description="Custom request headers")


class LinkCreate(LinkBase):
    pass


class LinkCrawl(LinkBase):
    pass


class LinkResponse(LinkBase):
    id: int
    title: Optional[str] = None
    favicon: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class LinkCrawlResponse(LinkBase):
    status: str

    class Config:
        from_attributes = True


class BulkLinkCreate(schemas.BaseModel):
    urls: List[HttpUrl]
    headers: Optional[Dict[str, str]] = Field(
        default=settings.DEFAULT_HEADERS, description="Custom request headers to use for all URLs")


class BulkLinkResponse(schemas.BaseModel):
    links_added: int

    class Config:
        from_attributes = True
