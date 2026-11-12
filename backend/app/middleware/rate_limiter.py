"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RATE LIMITING MIDDLEWARE & DEPENDENCY — Task Chống Spam Request            ║
║  Đồ án sinh viên: Thiết kế đơn giản, dễ hiểu, lưu trữ trong RAM (In-Memory)  ║
║  Không cần cài đặt Redis hay cấu hình phức tạp.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Nguyên lý hoạt động (Cơ chế Sliding Window):
1. Mỗi khi người dùng gửi request, server lấy IP của client.
2. Lưu các mốc thời gian (timestamp) mà IP đó đã gọi API vào một danh sách.
3. Khi có request mới:
   - Xóa bỏ các mốc thời gian cũ hơn khoảng thời gian quy định (window_seconds).
   - Đếm số request còn lại trong khoảng thời gian này.
   - Nếu số lượt gọi >= max_requests: Chặn lại và trả về lỗi HTTP 429 (Too Many Requests).
   - Nếu chưa vượt quá: Thêm mốc thời gian hiện tại vào và cho phép request đi tiếp.
"""

import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.handleExp import TooManyRequestsError


# Bộ nhớ RAM lưu lịch sử request theo IP:
# Cấu trúc: { "127.0.0.1": [1731380000.1, 1731380005.4, ...] }
_ip_request_history: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """
    Hàm tiện ích lấy địa chỉ IP của Client.
    Hỗ trợ trường hợp client đứng sau Proxy / Nginx qua header X-Forwarded-For.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# ─────────────────────────────────────────────────────────────────────────────
# CÁCH 1: Dùng làm Dependency cho từng Endpoint nhạy cảm (Khuyên dùng)
# ─────────────────────────────────────────────────────────────────────────────
class RateLimiter:
    """
    FastAPI Dependency để gắn vào các endpoint cụ thể cần chống spam.
    
    Ví dụ sử dụng trong router:
        from fastapi import APIRouter, Depends
        from app.middleware.rate_limiter import RateLimiter

        router = APIRouter()

        # Giới hạn người dân chỉ được gửi tối đa 5 báo cáo ngập trong 60 giây
        @router.post("/floods", dependencies=[Depends(RateLimiter(max_requests=5, window_seconds=60))])
        async def create_flood_report(...):
            return {"message": "Thành công"}
    """

    def __init__(self, max_requests: int | None = None, window_seconds: int = 60):
        # Nếu không truyền max_requests, lấy mặc định từ biến RATE_LIMIT_PER_MINUTE trong file .env
        self.max_requests = max_requests or getattr(settings, "RATE_LIMIT_PER_MINUTE", 60)
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        client_ip = get_client_ip(request)
        now = time.time()

        # Lấy danh sách lịch sử gọi API của IP này
        timestamps = _ip_request_history[client_ip]

        # 1. Loại bỏ các mốc thời gian cũ hơn cửa sổ window_seconds
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        _ip_request_history[client_ip] = valid_timestamps

        # 2. Kiểm tra nếu số lần gọi vượt quá mức cho phép
        if len(valid_timestamps) >= self.max_requests:
            remaining_wait = int(self.window_seconds - (now - valid_timestamps[0]))
            raise TooManyRequestsError(
                f"Bạn thao tác quá nhanh! Giới hạn cho phép: {self.max_requests} lần / {self.window_seconds} giây. "
                f"Vui lòng đợi {max(remaining_wait, 1)} giây nữa trước khi thử lại."
            )

        # 3. Ghi nhận thời điểm gửi request hợp lệ này
        _ip_request_history[client_ip].append(now)


# ─────────────────────────────────────────────────────────────────────────────
# CÁCH 2: Dùng làm Middleware tự động bảo vệ toàn bộ Endpoint nhạy cảm
# ─────────────────────────────────────────────────────────────────────────────
# Danh sách các đường dẫn nhạy cảm cần tự động bảo vệ chống spam (như tạo báo cáo ngập, kiểm tra ngập)
SENSITIVE_PATHS = [
    "/api/v1/floods",
    "/api/v1/routes/check-flood",
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware tự động chặn spam trên toàn bộ hệ thống hoặc các đường dẫn nhạy cảm.
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # Chỉ kiểm tra Rate Limit đối với các phương thức gửi dữ liệu (POST, PUT, DELETE)
        # hoặc các endpoint nằm trong danh sách nhạy cảm
        is_sensitive_path = any(request.url.path.startswith(p) for p in SENSITIVE_PATHS)
        is_modifying_method = request.method in ["POST", "PUT", "DELETE"]

        if is_sensitive_path and is_modifying_method:
            client_ip = get_client_ip(request)
            now = time.time()

            timestamps = _ip_request_history[client_ip]
            valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
            _ip_request_history[client_ip] = valid_timestamps

            # Đối với endpoint nhạy cảm (như gửi báo cáo), giới hạn chặt hơn (ví dụ 10 lần/phút)
            limit = 10 if "/floods" in request.url.path else self.max_requests

            if len(valid_timestamps) >= limit:
                remaining_wait = int(self.window_seconds - (now - valid_timestamps[0]))
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "code": 429,
                        "message": (
                            f"Bạn thao tác quá nhanh! Giới hạn: {limit} lần/{self.window_seconds}s. "
                            f"Vui lòng đợi {max(remaining_wait, 1)} giây trước khi gửi tiếp."
                        ),
                    },
                )

            _ip_request_history[client_ip].append(now)

        # Cho phép request tiếp tục chạy bình thường
        response = await call_next(request)
        return response


def setup_rate_limiting(app) -> None:
    """Hàm hỗ trợ gắn RateLimitMiddleware vào FastAPI trong main.py."""
    limit = getattr(settings, "RATE_LIMIT_PER_MINUTE", 60)
    app.add_middleware(RateLimitMiddleware, max_requests=limit, window_seconds=60)
