# backend/database.py
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.config import settings

# Create base model
Base = declarative_base()

# Create synchronous engine for initial setup
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+aiosqlite", ""),
    connect_args={"check_same_thread": False}
)

# Create async engine for FastAPI
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)

# Create tables


def create_db_and_tables():
    Base.metadata.create_all(sync_engine)

# Get async session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
