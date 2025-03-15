# backend/config.py
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Dict


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./inquisitive.db"

    # JWT settings
    # In production, use a secure key
    SECRET_KEY: str = "YOUR_SECRET_KEY_CHANGE_THIS"
    RESET_PASSWORD_TOKEN_SECRET: str = "YOUR_SECRET_KEY_CHANGE_THIS"
    VERIFICATION_TOKEN_SECRET: str = "YOUR_SECRET_KEY_CHANGE_THIS"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 30  # 30 days
    JWT_TOKEN_AUDIENCE: str = "fastapi-users:auth"

    # CORS settings
    # Streamlit default port
    CORS_ORIGINS: list[str] = ["http://localhost:8501"]

    UPLOAD_DIR: Path = Path("./uploads")
    UPLOAD_DIR.mkdir(exist_ok=True)
    EMBEDDINGS_MODEL: str = "chroma/all-minilm-l6-v2-f32"

    VECTOR_STORE_PERSISTS_DIRECTORY: str = "./chroma_db"
    WINDOW_SIZE_MULTIPLIER: int = 10
    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    class Config:
        env_file = ".env"


settings = Settings()
