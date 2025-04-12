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
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FileUploadDB(schemas.BaseModel):
    id: int
    filename: str
    original_filename: str
    file_path: str
    file_url: str
    content_type: str
    created_at: datetime
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
    updated_at: Optional[datetime] = None

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


class DocumentSearchRequest(schemas.BaseModel):
    prompt: str
    include_sources: Optional[List[str]] = None
    exclude_sources: Optional[List[str]] = None
    window_size: Optional[int] = 5
    source_type: Optional[str] = None


class DocumentMetadata(schemas.BaseModel):
    source: str
    page: str
    source_type: str
    belongs_to: str
    title: Optional[str] = None
    link_id: Optional[str] = None
    file_id: Optional[str] = None
    filename: Optional[str] = None


class DocumentResult(schemas.BaseModel):
    page_content: str
    metadata: DocumentMetadata
    score: float


class DocumentSearchResponse(schemas.BaseModel):
    documents: List[DocumentResult]
    count: int


class NoteCreateRequest(schemas.BaseModel):
    content: str
    title: str


class NoteUpdateRequest(schemas.BaseModel):
    content: str


class NoteUpdateResponse(schemas.BaseModel):
    filename: str
    updated: bool


class NoteCreateResponse(schemas.BaseModel):
    id: int
    url: str
    title: str
    status: str


class NoteResponse(schemas.BaseModel):
    id: int
    url: str
    title: str
    filename: str
    created_at: datetime
    updated_at: datetime


class NoteList(schemas.BaseModel):
    notes: List[NoteResponse]
    total: int


class LinksList(schemas.BaseModel):
    links: List[LinkResponse]
    total: int


class FilesList(schemas.BaseModel):
    files: List[FileUploadResponse]
    total: int


class FilePollingResponse(schemas.BaseModel):
    status: str


class ResourceDeletedResponse(schemas.BaseModel):
    status: str
