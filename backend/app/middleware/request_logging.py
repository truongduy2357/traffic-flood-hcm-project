
"""
REQUEST LOGGING MIDDLEWARE
Theo dõi lịch sử truy cập API.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from app.core.logging_config import get_logger

logger = get_logger("api_access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        start_time = time.perf_counter()

        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)

            duration = (
                time.perf_counter() - start_time
            ) * 1000

            log_message = (
                f"IP={client_ip} | "
                f"METHOD={method} | "
                f"PATH={path} | "
                f"STATUS={response.status_code} | "
                f"DURATION={duration:.2f}ms"
            )

            if response.status_code >= 500:
                logger.error(log_message)
            elif response.status_code >= 400:
                logger.warning(log_message)
            else:
                logger.info(log_message)

            return response

        except Exception:
            duration = (
                time.perf_counter() - start_time
            ) * 1000

            logger.exception(
                "API_EXCEPTION | IP=%s | METHOD=%s | "
                "PATH=%s | DURATION=%.2fms",
                client_ip,
                method,
                path,
                duration,
            )

            raise


def setup_request_logging(app):
    """Đăng ký middleware logging vào FastAPI."""
    app.add_middleware(RequestLoggingMiddleware)
