
"""
LOGGING CONFIGURATION
Cấu hình ghi log cho hệ thống FastAPI.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Thư mục backend/logs
BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"


def setup_logging():
    """Khởi tạo hệ thống logging."""

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Ghi log ra file, tối đa 5MB/file, giữ 5 file backup
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Đồng thời hiển thị log trên terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str):
    """Lấy logger theo tên module."""
    return logging.getLogger(f"app.{name}")
