import asyncio
import aiohttp
from bs4 import BeautifulSoup

from backend.api.models import Link, ProcessingStatus
from backend.vector_store import add_link_content_to_vector_store
from backend.core.logging import get_logger
from urllib.parse import urlparse
from backend.database import async_session_maker
from sqlalchemy import select


# import logging
logger = get_logger()

# Create a queue for background processing
url_processing_queue = asyncio.Queue()
concurrency_limit = asyncio.Semaphore(4)

# Helper function to get base URL


def get_base_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def process_url_queue():
    while True:
        try:
            # Get an item from the queue
            link_id, url, user_email, headers = await url_processing_queue.get()

            # Process the URL in a separate task to avoid blocking the queue
            asyncio.create_task(process_single_url(
                link_id, url, user_email, headers))

            # Mark the queue task as done
            url_processing_queue.task_done()

        except Exception as e:
            logger.error(f"Error in URL processing queue: {str(e)}")
            await asyncio.sleep(1)  # P


def extract_metadata_from_html(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')

    text = soup.get_text()

    # Extract title
    title = soup.title.string if soup.title else None

    # Extract favicon
    favicon = None
    favicon_link = soup.find('link', rel=lambda r: r and (
        'icon' in r.lower() or 'shortcut icon' in r.lower()))
    if favicon_link and favicon_link.get('href'):
        favicon_url = favicon_link['href']
        # Handle relative URLs
        if favicon_url.startswith('/'):
            favicon = f"{base_url}{favicon_url}"
        else:
            favicon = favicon_url

    return title, favicon, text


# Background task to process URLs from the queue
async def process_single_url(link_id, url, user_email, headers):
    # Acquire the semaphore to limit concurrency
    async with concurrency_limit:
        logger.info(
            f"Processing URL {url} for user {user_email} (link ID: {link_id})")

        # Create a new session for this task
        async with async_session_maker() as db:
            try:
                # Update status to in progress
                stmt = select(Link).where(Link.id == link_id)
                result = await db.execute(stmt)
                link = result.scalars().first()

                if not link:
                    logger.error(f"Link with ID {link_id} not found")
                    return

                link.status = ProcessingStatus.IN_PROGRESS
                await db.commit()

                # Fetch URL content
                async with aiohttp.ClientSession() as session:
                    try:
                        request_kwargs = {
                            "timeout": 30,
                            "allow_redirects": True,
                            "max_redirects": 10,
                            "headers": headers
                        }
                        async with session.get(url, **request_kwargs) as response:
                            if response.status == 200:
                                html_content = await response.text()
                                # Get the base URL for resolving relative URLs
                                base_url = get_base_url(str(response.url))

                                # Extract title and favicon
                                title, favicon, text_content = extract_metadata_from_html(
                                    html_content, base_url)

                                # Update link with metadata
                                link.title = title
                                link.favicon = favicon

                                # Add to vector store
                                await asyncio.to_thread(add_link_content_to_vector_store,
                                                        text_content, url, title, link_id, user_email)

                                # Update status to finished
                                link.status = ProcessingStatus.FINISHED
                                logger.info(
                                    f"Successfully processed URL {url} for user {user_email}")
                            else:
                                logger.error(
                                    f"Failed to fetch URL {url}: HTTP status {response.status}")
                                link.status = ProcessingStatus.FAILED
                    except Exception as e:
                        logger.error(f"Error fetching URL {url}: {str(e)}")
                        link.status = ProcessingStatus.FAILED

                # Commit changes
                await db.commit()

            except Exception as e:
                logger.error(
                    f"Error processing URL {url} for user {user_email}: {str(e)}")
                # Try to mark the link as failed if possible
                try:
                    if link:
                        link.status = ProcessingStatus.FAILED
                        await db.commit()
                except:
                    pass
