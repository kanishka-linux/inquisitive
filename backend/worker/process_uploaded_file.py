import asyncio

from backend.api.models import FileUpload, ProcessingStatus, Note
from backend.vector_store import add_uploaded_document_content_to_vector_store
from backend.core.logging import get_logger
from backend.database import async_session_maker
from sqlalchemy import select, func
from datetime import datetime


# import logging
logger = get_logger()

# Create a queue for background processing
file_processor_queue = asyncio.Queue()
concurrency_limit = asyncio.Semaphore(4)


async def process_uploaded_file_queue():
    while True:
        try:
            # Get an item from the queue
            file_path, file_name, file_url, file_id, user_email, source_type = await file_processor_queue.get()

            # Process the URL in a separate task to avoid blocking the queue
            asyncio.create_task(process_file(
                file_path, file_name, file_url, file_id, user_email, source_type))

            # Mark the queue task as done
            # file_processor_queue.task_done()

        except Exception as e:
            logger.error(f"Error in URL processing queue: {str(e)}")
            await asyncio.sleep(1)  # P


# Background task to process URLs from the queue
async def process_file(
        file_path,
        file_name,
        file_url,
        file_id,
        user_email,
        source_type):
    # Acquire the semaphore to limit concurrency
    async with concurrency_limit:
        async with async_session_maker() as db:
            try:
                await asyncio.to_thread(
                    add_uploaded_document_content_to_vector_store,
                    file_path,
                    file_name,
                    file_url,
                    file_id,
                    user_email
                )

                if source_type == "note":
                    stmt = select(Note).where(Note.id == file_id)
                else:
                    stmt = select(FileUpload).where(FileUpload.id == file_id)
                result = await db.execute(stmt)
                file_row = result.scalars().first()

                file_row.status = ProcessingStatus.FINISHED
                file_row.updated_at = func.now()
                await db.commit()

                file_processor_queue.task_done()
                logger.info(
                    f"Successfully processed File: {file_name} for user {user_email}")
            except Exception as e:
                logger.error(
                    f"Error Processing file: {file_name} for user {user_email}: {str(e)}")
