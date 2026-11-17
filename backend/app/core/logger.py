"""
Cấu hình Logging tập trung cho hệ thống (Hỗ trợ UTF-8 cho Windows console)
"""
import logging
import sys
import io

def setup_logger(name: str = "traffic_flood_app") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Đảm bảo UTF-8 stream trên Windows console
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

app_logger = setup_logger("traffic_flood")
