# backend/config.py
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Dict
from backend.vector_store.models import StoreEngine
import os
import json


def get_env_file_path():
    """Get the path to the .env file in the base directory"""
    home_dir = os.path.expanduser("~")
    base_dir = os.path.join(home_dir, ".config", "inquisitive")

    Path(base_dir).mkdir(parents=True, exist_ok=True)

    env_file_path = os.path.join(base_dir, "backend.env")

    if not os.path.exists(env_file_path):
        with open(env_file_path, 'w') as f:
            f.write("# Backend environment variables for Inquisitive\n")

    return env_file_path


# It is possible to override all the defaults values
# by specifying env variables or adding variables in backend.env.
# However, if we decide to override default directory locations
# then we need to make sure that one needs to create
# all the relevant directories and sub-directories
# manually
class Settings(BaseSettings):
    # BASIC SERVER SETTINGS
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_LOG_LEVEL: str = "debug"

    # BASIC DIRECTORY CREATION
    HOME_DIR: str = os.path.expanduser("~")
    CONFIG_DIR: str = os.path.join(HOME_DIR, ".config")
    CONFIG_DIR_PATH: Path = Path(CONFIG_DIR)
    CONFIG_DIR_PATH.mkdir(exist_ok=True)

    BASE_DIR: str = os.path.join(CONFIG_DIR, "inquisitive")
    BASE_DIR_PATH: Path = Path(BASE_DIR)
    BASE_DIR_PATH.mkdir(exist_ok=True)

    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    UPLOAD_DIR_PATH: Path = Path(UPLOAD_DIR)
    UPLOAD_DIR_PATH.mkdir(exist_ok=True)

    LINKS_JOB_QUEUE_CONCURRENCY: int = 100
    FILES_JOB_QUEUE_CONCURRENCY: int = 50

    # Sqlite Path
    SQLITE_DB_PATH: str = os.path.join(BASE_DIR, "inquisitive.db")

    # Vector store path
    CHROMA_VECTOR_STORE_PERSISTS_DIRECTORY: str = os.path.join(
        BASE_DIR, "chroma_db")
    MILVUS_VECTOR_STORE_URL: str = os.path.join(BASE_DIR, "milvus_data.db")
    LANCE_DB_VECTOR_STORE_PERSISTS_DIRECTOY: str = os.path.join(
        BASE_DIR, "lance_db")

    # Default vector database
    DEFAULT_VECTOR_DB: str = StoreEngine.LANCE

    VECTOR_STORE_COLLECTION_NAME: str = "document_store"

    # Modify and use different embedding model if needed
    EMBEDDINGS_MODEL: str = "chroma/all-minilm-l6-v2-f32"
    EMBEDDINGS_DIMENSION: int = 384
    TEXT_SPLITTER_CHUNK_SIZE:  int = 1500
    TEXT_SPLITTER_CHUNK_OVERLAP:  int = 150

    # Modify if needed to use other relational DB
    DATABASE_URL: str = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"

    # JWT settings
    # In production, use a secure key
    SECRET_KEY: str = "YOUR_SECRET_KEY_CHANGE_THIS"
    RESET_PASSWORD_TOKEN_SECRET: str = "YOUR_SECRET_KEY_CHANGE_THIS"
    VERIFICATION_TOKEN_SECRET: str = "YOUR_SECRET_KEY_CHANGE_THIS"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 30  # 30 days
    JWT_TOKEN_AUDIENCE: str = "fastapi-users:auth"

    # CORS settings
    # Streamlit UI default port
    CORS_ORIGINS: list[str] = ["http://localhost:8501"]
    WINDOW_SIZE_MULTIPLIER: int = 10
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
            elif field_name == "CORS_ORIGINS":
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    return [item.strip() for item in raw_val.split(',')]
            return raw_val


settings = Settings()
