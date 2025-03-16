# frontend/config.py
from pydantic_settings import BaseSettings
from typing import Dict


class Settings(BaseSettings):
    API_URL: str = "http://localhost:8000"
    LIST_PAGE_SIZE: int = 5
    ALLOW_AUTO_USER_REGISTER: bool = True
    UPLOAD_FILE_TYPES: list[str] = ['txt', 'pdf', "md", "json", "sh"]
    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    class Config:
        env_file = ".env"


settings = Settings()
