# frontend/config.py
from pydantic_settings import BaseSettings
from typing import Dict


class Settings(BaseSettings):
    API_URL: str = "http://localhost:8000"
    LIST_PAGE_SIZE: int = 5
    ALLOW_AUTO_USER_REGISTER: bool = True
    UPLOAD_FILE_TYPES: list[str] = ['txt', 'pdf', "md", "json", "sh"]
    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    class Config:
        env_file = ".env"


settings = Settings()
