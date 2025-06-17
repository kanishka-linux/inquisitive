# frontend/config.py
from pydantic_settings import BaseSettings
from typing import Dict
import os
import json
from pathlib import Path


def get_env_file_path():
    """Get the path to the .env file in the base directory"""
    home_dir = os.path.expanduser("~")
    base_dir = os.path.join(home_dir, ".config", "inquisitive")

    Path(base_dir).mkdir(parents=True, exist_ok=True)

    env_file_path = os.path.join(base_dir, "frontend.env")

    # Create an empty .env file if it doesn't exist
    if not os.path.exists(env_file_path):
        with open(env_file_path, 'w') as f:
            f.write("# Frontend Environment variables for Inquisitive\n")

    return env_file_path


class Settings(BaseSettings):
    SERVER_PORT: int = 8501
    SERVER_HOST: str = "0.0.0.0"

    OLLAMA_HOST: str = "http://0.0.0.0:11434"

    # FastAPI Backend URL (http://{HOST}:{PORT})
    API_URL: str = "http://localhost:8000"
    LIST_PAGE_SIZE: int = 5
    ALLOW_AUTO_USER_REGISTER: bool = True
    # default editors - streamlit_default, easymde
    DEFAULT_EDITOR: str = "easymde"
    UPLOAD_FILE_TYPES: list[str] = ['txt', 'pdf', "md", "json", "sh"]
    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    class Config:
        env_file = get_env_file_path()
        env_file_encoding = 'utf-8'

        @classmethod
        def parse_env_var(cls, field_name, raw_val):
            if field_name == "DEFAULT_HEADERS":
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    return {}
            elif field_name == "UPLOAD_FILE_TYPES":
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    return [item.strip() for item in raw_val.split(',')]
            return raw_val


settings = Settings()
