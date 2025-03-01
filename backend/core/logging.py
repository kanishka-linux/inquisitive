# core/logging.py

import logging
import sys
from pathlib import Path
from loguru import logger
from pydantic import BaseModel
from typing import Dict, Any

# Configuration for loguru


class LogConfig(BaseModel):
    """Logging configuration"""
    LOGGER_NAME: str = "fastapi_app"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    LOG_LEVEL: str = "INFO"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Dict[str, str]] = {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(message)s",
        },
    }
    handlers: Dict[str, Dict[str, Any]] = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    }
    loggers: Dict[str, Dict[str, Any]] = {
        "": {  # root logger
            "handlers": ["default", "file"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "uvicorn": {
            "handlers": ["default", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["default", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    }


# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Setup logging configuration


def setup_logging():
    """Configure logging"""
    config = LogConfig()
    logging.config.dictConfig(config.dict())

    # Intercept standard library logging
    logging.getLogger("uvicorn").handlers = []

    # Configure loguru
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "format": config.LOG_FORMAT,
                "level": config.LOG_LEVEL,
            },
            {
                "sink": "logs/app.log",
                "format": config.LOG_FORMAT,
                "level": config.LOG_LEVEL,
                "rotation": "10 MB",
                "retention": "1 week",
                "compression": "zip",
            },
        ]
    )

    return logger

# Create a function to get logger


def get_logger(name: str = None):
    """Get logger with the given name"""
    return logging.getLogger(name or "fastapi_app")
