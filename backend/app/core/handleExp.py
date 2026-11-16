
"""
APPLICATION EXCEPTION HANDLER
Quản lý ngoại lệ và ghi log lỗi hệ thống cho FastAPI.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger


# Logger dành cho xử lý ngoại lệ
logger = get_logger("exceptions")


# ============================================================
# 1. LỚP LỖI CHA (BASE EXCEPTION)
# ============================================================

class AppException(Exception):
    status_code: int = 500
    message: str = "Lỗi hệ thống"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message

        super().__init__(self.message)


# ============================================================
# 2. CÁC LỚP LỖI CON THƯỜNG DÙNG
# ============================================================

class BadRequestError(AppException):
    status_code = 400
    message = "Dữ liệu gửi lên không hợp lệ"


class ForbiddenError(AppException):
    status_code = 403
    message = "Bạn không có quyền truy cập"


class NotFoundError(AppException):
    status_code = 404
    message = "Không tìm thấy dữ liệu"


class TooManyRequestsError(AppException):
    status_code = 429
    message = "Bạn gửi yêu cầu quá nhanh! Vui lòng thử lại sau ít phút."


# ============================================================
# 3. HÀM BẮT LỖI VÀ GHI LOG
# ============================================================

async def handle_app_exception(
    request: Request,
    exc: AppException,
):
    """
    Xử lý ngoại lệ tùy chỉnh.

    - Ghi log lỗi theo HTTP status code.
    - Ghi nhận HTTP method và API endpoint.
    - Trả về JSON response chuẩn cho Frontend.
    """

    log_message = (
        "APPLICATION_EXCEPTION | "
        f"METHOD={request.method} | "
        f"PATH={request.url.path} | "
        f"STATUS={exc.status_code} | "
        f"MESSAGE={exc.message}"
    )

    # Lỗi hệ thống 5xx: ghi log mức ERROR
    if exc.status_code >= 500:
        logger.error(log_message)

    # Lỗi phía client 4xx: ghi log mức WARNING
    else:
        logger.warning(log_message)

    # Trả kết quả lỗi chuẩn cho Frontend
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.status_code,
            "message": exc.message,
        },
    )
