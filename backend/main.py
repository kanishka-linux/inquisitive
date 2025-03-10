# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import router as auth_router
from backend.api.router import file_router, link_router
from backend.worker.url_processor import process_url_queue
from backend.worker.url_processor_recursive import process_recursive_url_queue
from backend.worker.process_uploaded_file import process_uploaded_file_queue
from backend.config import settings
from backend.database import create_db_and_tables
from backend.core.logging import setup_logging
import asyncio

logger = setup_logging()

# Create FastAPI app
app = FastAPI(title="FastAPI Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth")
app.include_router(file_router, prefix="/file")
app.include_router(link_router, prefix="/links")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    asyncio.create_task(process_url_queue())
    asyncio.create_task(process_recursive_url_queue())
    asyncio.create_task(process_uploaded_file_queue())

# Root endpoint


@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI API Backend"}
