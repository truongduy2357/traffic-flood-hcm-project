from fastapi import Request
from fastapi.responses import JSONResponse


# 1. Lớp lỗi cha (Base Exception)
class AppException(Exception):
    status_code: int = 500
    message: str = "Lỗi hệ thống"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


# 2. Các lớp lỗi con thường dùng
class BadRequestError(AppException):
    status_code = 400
    message = "Dữ liệu gửi lên không hợp lệ"


class ForbiddenError(AppException):
    status_code = 403
    message = "Bạn không có quyền truy cập"


class NotFoundError(AppException):
    status_code = 404
    message = "Không tìm thấy dữ liệu"


# 3. Hàm bắt lỗi và trả về JSON chuẩn cho Frontend
async def handle_app_exception(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.status_code,
            "message": exc.message,
        },
    )