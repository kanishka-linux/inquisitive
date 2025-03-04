# backend/config.py
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./users.db"

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

    class Config:
        env_file = ".env"


settings = Settings()
