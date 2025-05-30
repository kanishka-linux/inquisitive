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
from sqlalchemy import select, desc, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import (
    auth_backend,
    current_active_user,
    fastapi_users,
)

from backend.core.utils import save_file, update_file_with_backup

from backend.worker.url_processor import url_processing_queue
from backend.worker.url_processor_recursive import recursive_url_processing_queue
from backend.worker.process_uploaded_file import file_processor_queue
from backend.vector_store.adapter import vector_db

from backend.api.models import (
    User,
    FileUpload,
    ProcessingStatus,
    Link,
    Note
)
from backend.api.schemas import (
    TokenPayload,
    UserCreate,
    UserRead,
    UserUpdate,
    FileUploadResponse,
    LinkCreate,
    LinkResponse,
    BulkLinkCreate,
    BulkLinkResponse,
    LinkCrawl,
    LinkCrawlResponse,
    DocumentSearchResponse,
    DocumentSearchRequest,
    DocumentResult,
    DocumentMetadata,
    NoteCreateRequest,
    NoteCreateResponse,
    NoteList,
    NoteResponse,
    NoteUpdateRequest,
    NoteUpdateResponse,
    LinksList,
    FilesList,
    FilePollingResponse,
    ResourceDeletedResponse
)
from backend.api.service import validate_jwt_token
from backend.database import get_async_session
from backend.core.logging import get_logger

from backend.config import settings
import os
import uuid
import shutil
from pathlib import Path


vector_store = vector_db()

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
link_router = APIRouter(tags=["links"])
document_router = APIRouter(tags=["documents"])

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
@file_router.post("/upload", response_model=FileUploadResponse, status_code=202)
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

    if file.filename.endswith('.md'):
        source_type = "note"

        file_url = f"/file/note/{unique_filename}"

        db_note = Note(
            url=file_url,
            title=file.filename,
            filename=unique_filename,
            file_path=str(file_path),
            status=ProcessingStatus.PENDING,
            user_id=user.id
        )
        session.add(db_note)
        await session.commit()
        await session.refresh(db_note)

        file_id = db_note.id
        created_at = db_note.created_at

    else:
        source_type = "file"

        file_url = f"/file/{unique_filename}"

        # Create a database entry
        db_file = FileUpload(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_url=file_url,
            status=ProcessingStatus.PENDING,
            content_type=file.content_type,
            user_id=user.id
        )
        session.add(db_file)
        await session.commit()
        await session.refresh(db_file)

        file_id = db_file.id
        created_at = db_file.created_at

    await file_processor_queue.put(
        (
            file_path,
            unique_filename,
            file_url,
            file_id,
            user.email,
            source_type
        )
    )
    # Return the file URL to the client
    return {
        "filename": unique_filename,
        "file_url": file_url,
        "status": ProcessingStatus.PENDING,
        "created_at": created_at
    }


# Files List endpoint
@file_router.get("/", response_model=FilesList, status_code=200)
async def list_uploaded_files(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    stmt = (
        select(FileUpload)
        .where(FileUpload.user_id == user.id)
        .order_by(desc(FileUpload.updated_at))
        .offset(skip)
        .limit(limit)
    )

    result = await session.execute(stmt)
    records = result.scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(FileUpload)
        .where(FileUpload.user_id == user.id)
    )

    total_count = await session.execute(count_stmt)
    total_count = total_count.scalar() or 0

    result = [
        FileUploadResponse(
            file_url=record.file_url,
            filename=record.filename,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at
        ) for record in records
    ]
    # Return the file URL to the client
    return FilesList(
        files=result,
        total=total_count
    )


# Note upload endpoint
@file_router.post("/note", response_model=NoteCreateResponse, status_code=202)
async def create_note(
    note: NoteCreateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    doc_id, file_path, filename, saved = save_file(note.content, note.title)

    if not saved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Error creating file"
        )

    file_url = f"/file/note/{filename}"

    # Create a database entry
    db_note = Note(
        url=file_url,
        title=note.title,
        filename=filename,
        file_path=str(file_path),
        status=ProcessingStatus.PENDING,
        user_id=user.id
    )

    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)

    await file_processor_queue.put(
        (file_path, filename, file_url, db_note.id, user.email, "note")
    )
    # Return the file URL to the client
    return NoteCreateResponse(
        id=db_note.id,
        url=file_url,
        title=note.title,
        status=db_note.status
    )


# Note List endpoint
@file_router.get("/note", response_model=NoteList, status_code=200)
async def list_notes(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    stmt = (
        select(Note)
        .where(Note.user_id == user.id)
        .order_by(desc(Note.updated_at))
        .offset(skip)
        .limit(limit)
    )

    result = await session.execute(stmt)
    records = result.scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(Note)
        .where(Note.user_id == user.id)
    )

    total_count = await session.execute(count_stmt)
    total_count = total_count.scalar() or 0

    result = [
        NoteResponse(
            url=record.url,
            id=record.id,
            title=record.title,
            filename=record.filename,
            created_at=record.created_at,
            updated_at=record.updated_at
        ) for record in records
    ]
    # Return the file URL to the client
    return NoteList(
        notes=result,
        total=total_count
    )


@file_router.get("/note/{filename}")
async def get_note(
    filename: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Check if the file exists in the database
    result = await session.execute(
        select(Note).where(Note.filename == filename)
    )
    note_record = result.scalars().first()

    if not note_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Check if the user has access to the file
    if note_record.user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file"
        )

    # Check if the file exists on disk
    file_path = Path(note_record.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )

    # Return the file as a response
    return FileResponse(
        path=file_path,
        filename=note_record.title,
        media_type="text/markdown"
    )


@file_router.patch(
    "/note/{filename}",
    response_model=NoteUpdateResponse,
    status_code=200)
async def update_note(
    filename: str,
    note: NoteUpdateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Note)
        .where(Note.filename == filename, Note.user_id == user.id)
    )
    note_record = result.scalars().first()
    note_record.status = ProcessingStatus.PENDING
    await session.commit()

    if not note_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    updated = update_file_with_backup(note.content, note_record.filename)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Error updating file"
        )

    # remove existing vector documents
    # and then add new set of updated documents
    vector_store.remove_documents(
        note_record.filename,
        user.email
    )

    await file_processor_queue.put(
        (
            note_record.file_path,
            note_record.filename,
            note_record.url,
            note_record.id,
            user.email,
            "note"
        )
    )

    return NoteUpdateResponse(
        filename=note_record.filename,
        updated=True
    )


@file_router.delete(
    "/note/{filename}",
    response_model=ResourceDeletedResponse,
    status_code=200)
async def delete_note(
    filename: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):

    result = await session.execute(
        select(Note)
        .where(Note.filename == filename, Note.user_id == user.id)
    )
    notes = result.scalars().all()

    if len(notes) == 1:
        note = notes[0]
        await session.execute(
            delete(Note).where(Note.id == note.id)
        )
        vector_store.remove_documents(
            note.filename,
            user.email
        )
        await session.commit()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return ResourceDeletedResponse(status="deleted")


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
    if file_record.user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file"
        )

    # Check if the file exists on disk
    file_path = Path(file_record.file_path)
    if not file_path.exists():
        file_path = os.path.join(settings.UPLOAD_DIR, file_record.filename)
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


@file_router.delete(
    "/{filename}",
    response_model=ResourceDeletedResponse,
    status_code=200)
async def delete_uploaded_file(
    filename: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):

    result = await session.execute(
        select(FileUpload)
        .where(FileUpload.filename == filename, FileUpload.user_id == user.id)
    )
    files = result.scalars().all()

    if len(files) == 1:
        fl = files[0]
        await session.execute(
            delete(FileUpload).where(FileUpload.id == fl.id)
        )
        vector_store.remove_documents(
            fl.filename,
            user.email
        )
        await session.commit()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return ResourceDeletedResponse(status="deleted")


@file_router.get(
    "/status/{filename}",
    response_model=FilePollingResponse,
    status_code=200)
async def get_file_status(
    filename: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Check if the file exists in the database
    result = await session.execute(
        select(FileUpload).where(
            FileUpload.filename == filename,
            FileUpload.user_id == user.id
        )
    )
    file_record = result.scalars().first()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return FilePollingResponse(
        status=file_record.status
    )


# Link submit endpoint
@link_router.post("/submit", response_model=LinkResponse, status_code=202)
async def submit_link(
    link: LinkCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    db_link = Link(
        url=str(link.url),
        user_id=user.id,
        status=ProcessingStatus.PENDING
    )
    session.add(db_link)
    await session.commit()
    await session.refresh(db_link)

    # Add to processing queue
    await url_processing_queue.put((db_link.id, str(link.url), user.email, link.headers))

    return db_link


# Bulk Links submit end-point
@link_router.post("/bulk", response_model=BulkLinkResponse, status_code=202)
async def submit_links_bulk(
    links_data: BulkLinkCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Process each URL
    successful_links = []
    failed_urls = []

    for url in links_data.urls:
        try:
            # Create new link entry
            db_link = Link(
                url=str(url),
                user_id=user.id,
                status=ProcessingStatus.PENDING
            )
            session.add(db_link)
            await session.commit()
            await session.refresh(db_link)

            # Add to processing queue with headers if provided
            await url_processing_queue.put((db_link.id, str(url), user.email, links_data.headers))

            successful_links.append(db_link)
        except Exception as e:
            failed_urls.append(str(url))

    return BulkLinkResponse(links_added=len(successful_links))


# Links List endpoint
@link_router.get("/", response_model=LinksList, status_code=200)
async def list_links(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    stmt = (
        select(Link)
        .where(Link.user_id == user.id)
        .order_by(desc(Link.updated_at))
        .offset(skip)
        .limit(limit)
    )

    result = await session.execute(stmt)
    records = result.scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(Link)
        .where(Link.user_id == user.id)
    )

    total_count = await session.execute(count_stmt)
    total_count = total_count.scalar() or 0

    result = [
        LinkResponse(
            url=record.url,
            id=record.id,
            title=record.title,
            favicon=record.favicon,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at
        ) for record in records
    ]
    # Return the file URL to the client
    return LinksList(
        links=result,
        total=total_count
    )


# Recursively Crawl the link
@link_router.post("/crawl", response_model=LinkCrawlResponse, status_code=202)
async def recursive_crawl(
    links_data: LinkCrawl,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):

    url = links_data.url
    await recursive_url_processing_queue.put((str(url), user, links_data.headers))

    return LinkCrawlResponse(status="submitted", url=url)


@link_router.delete(
    "/{id}",
    response_model=ResourceDeletedResponse,
    status_code=200)
async def delete_link(
    id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):

    result = await session.execute(
        select(Link)
        .where(Link.id == id, Link.user_id == user.id)
    )
    links = result.scalars().all()

    if len(links) == 1:
        link = links[0]
        await session.execute(
            delete(Link).where(Link.id == link.id)
        )
        vector_store.remove_link_documents(
            link.id,
            user.email
        )
        await session.commit()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return ResourceDeletedResponse(status="deleted")


@document_router.post("/search", response_model=DocumentSearchResponse, status_code=200)
async def search_documents(
    request: DocumentSearchRequest,
    user: User = Depends(current_active_user),
):
    try:

        window_size = request.window_size
        source_type = request.source_type
        docs = vector_store.fetch_documents(
            request.include_sources,
            request.exclude_sources,
            request.window_size,
            user.email,
            request.prompt,
            request.source_type
        )
        # Format results
        results = []
        uniq_sources = set()
        for doc, score in docs:
            source = doc.metadata.get("source", "")
            if source_type == "link" and len(uniq_sources) >= window_size:
                break
            if source_type == "link" and source in uniq_sources:
                continue

            results.append(
                DocumentResult(
                    page_content=doc.page_content,
                    metadata=DocumentMetadata(**doc.metadata),
                    score=score
                )
            )

            if source not in uniq_sources:
                uniq_sources.add(source)

        logger.info(
            f"doc received = {len(docs)}, uniq_sources = {len(uniq_sources)}")
        return DocumentSearchResponse(
            documents=results,
            count=len(results)
        )

    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error searching documents: {str(e)}")
