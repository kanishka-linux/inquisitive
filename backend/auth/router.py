# backend/auth/router.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import (
    auth_backend,
    current_active_user,
    fastapi_users,
)
from backend.auth.models import User, FileUpload
from backend.auth.schemas import (
    TokenPayload,
    UserCreate,
    UserRead,
    UserUpdate,
    FileUploadResponse
)
from backend.auth.service import validate_jwt_token
from backend.database import get_async_session
from backend.core.logging import get_logger

from backend.config import settings
import os
import uuid
import shutil
from pathlib import Path

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

file_router = APIRouter(tags=["files"])

# Custom token validation endpoint


@router.post("/validate-token", tags=["auth"])
async def validate_token(payload: TokenPayload):
    """Validate a JWT token and return user info if valid"""
    return validate_jwt_token(payload.token)


# Custom endpoint to get user by username
@router.get("/users/{username}", response_model=UserRead, tags=["users"])
async def get_user_by_username(
    username: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a user by username"""
    query = select(User).where(User.username == username)
    result = await session.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# File upload endpoint
@file_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Generate a unique filename to prevent collisions
    unique_filename = f"{uuid.uuid4()}-{file.filename}"

    # Create the file path
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate a URL for the file
    file_url = f"/file/{unique_filename}"

    # Create a database entry
    db_file = FileUpload(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_url=file_url,
        content_type=file.content_type,
        user_id=user.id
    )

    session.add(db_file)
    await session.commit()
    await session.refresh(db_file)

    # Return the file URL to the client
    return {
        "filename": file.filename,
        "file_url": file_url,
        "upload_time": db_file.upload_time
    }


@file_router.get("/{filename}")
async def get_file(
    filename: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Check if the file exists in the database
    result = await session.execute(
        select(FileUpload).where(FileUpload.filename == filename)
    )
    file_record = result.scalars().first()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check if the user has access to the file
    # (You might want to implement more complex access control)
    if file_record.user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file"
        )

    # Check if the file exists on disk
    file_path = Path(file_record.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )

    # Return the file as a response
    return FileResponse(
        path=file_path,
        filename=file_record.original_filename,
        media_type=file_record.content_type
    )
