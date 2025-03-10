import asyncio
from bs4 import BeautifulSoup
import re

from backend.api.models import Link, ProcessingStatus
from backend.vector_store import add_link_content_to_vector_store
from backend.core.logging import get_logger
from urllib.parse import urlparse
from backend.database import async_session_maker
from langchain_community.document_loaders import RecursiveUrlLoader


# import logging
logger = get_logger()

# Create a queue for background processing
recursive_url_processing_queue = asyncio.Queue()
concurrency_limit = asyncio.Semaphore(4)

# Helper function to get base URL


def get_base_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def process_recursive_url_queue():
    while True:
        try:
            # Get an item from the queue
            url, user, headers = await recursive_url_processing_queue.get()

            # Process the URL in a separate task to avoid blocking the queue
            asyncio.create_task(crawl_url(url, user, headers))

            # Mark the queue task as done
            recursive_url_processing_queue.task_done()

        except Exception as e:
            logger.error(f"Error in URL processing queue: {str(e)}")
            await asyncio.sleep(1)  # P


def bs4_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()


# Background task to process URLs from the queue
async def crawl_url(url, user, headers):
    loader = RecursiveUrlLoader(
        url,
        headers=headers,
        continue_on_failure=True,
        max_depth=2,
        timeout=300,
        use_async=True,
        extractor=bs4_extractor
    )
    # Acquire the semaphore to limit concurrency
    async with concurrency_limit:
        async with async_session_maker() as db:
            try:
                async for doc in loader.alazy_load():
                    title = doc.metadata.get("title", "No title")
                    text = doc.page_content.strip()
                    source = doc.metadata["source"]
                    db_link = Link(
                        url=str(source),
                        user_id=user.id,
                        status=ProcessingStatus.PENDING
                    )
                    db.add(db_link)
                    await db.commit()
                    await db.refresh(db_link)
                    await asyncio.to_thread(add_link_content_to_vector_store, text, source, title, db_link.id, user.email)
                    db_link.status = ProcessingStatus.FINISHED
                    await db.commit()
                    logger.info(
                        f"Successfully processed URL {source} for user {user.email}")

            except Exception as e:
                logger.error(
                    f"Error crawling URL {url} for user {user.email}: {str(e)}")
