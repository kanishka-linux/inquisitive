# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.router import router as auth_router
from backend.config import settings
from backend.database import create_db_and_tables
from backend.core.logging import setup_logging

logger = setup_logging()

# Create FastAPI app
app = FastAPI(title="FastAPI JWT Auth")

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

# Create database and tables on startup


@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Root endpoint


@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI JWT Auth API"}
