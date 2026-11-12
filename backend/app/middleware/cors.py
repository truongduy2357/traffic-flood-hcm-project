"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CORS MIDDLEWARE — Task 15 (SRS mục 2.1 & 3.1)                            ║
║                                                                            ║
║  Thiết lập Cross-Origin Resource Sharing cho phép trình duyệt Web          ║
║  (Chrome, Safari, Firefox, Edge) gọi API Backend không bị chặn bởi         ║
║  Same-Origin Policy.                                                       ║
║                                                                            ║
║  Sử dụng:                                                                  ║
║      from app.middleware.cors import setup_cors                            ║
║      setup_cors(app)                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Gắn CORSMiddleware vào ứng dụng FastAPI.

    Cho phép trình duyệt web hiện đại (Chrome, Safari, Firefox, Edge)
    gọi API Backend từ domain/port khác mà không bị chặn Same-Origin Policy.

    Tham số được cấu hình:
    ┌──────────────────────┬────────────────────────────────────────────────────┐
    │ allow_origins        │ Danh sách domain Frontend được phép gọi API.     │
    │                      │ Đọc từ biến CORS_ORIGINS trong file .env.        │
    ├──────────────────────┼────────────────────────────────────────────────────┤
    │ allow_credentials    │ Cho phép gửi cookie/JWT cross-origin.            │
    ├──────────────────────┼────────────────────────────────────────────────────┤
    │ allow_methods        │ GET, POST, PUT, DELETE, PATCH, OPTIONS.          │
    ├──────────────────────┼────────────────────────────────────────────────────┤
    │ allow_headers        │ Tất cả headers (Content-Type, Authorization,...).│
    ├──────────────────────┼────────────────────────────────────────────────────┤
    │ expose_headers       │ Headers tùy chỉnh mà JS được phép đọc.          │
    ├──────────────────────┼────────────────────────────────────────────────────┤
    │ max_age              │ Cache preflight 600s (10 phút).                  │
    └──────────────────────┴────────────────────────────────────────────────────┘

    Luồng CORS:
        Browser ──OPTIONS (preflight)──► FastAPI
        Browser ◄──Access-Control-Allow-Origin──
        Browser ──GET/POST (actual)──► FastAPI
        Browser ◄──200 OK + JSON──
    """

    # Xử lý CORS_ORIGINS: hỗ trợ cả list và string "*"
    origins = settings.CORS_ORIGINS
    if isinstance(origins, str):
        origins = [origins]

    app.add_middleware(
        CORSMiddleware,
        # Danh sách origin Frontend được phép truy cập API
        allow_origins=origins,
        # Cho phép gửi credentials (cookies, Authorization header) cross-origin
        allow_credentials=True,
        # Cho phép tất cả HTTP methods (GET, POST, PUT, DELETE, PATCH, OPTIONS)
        allow_methods=["*"],
        # Cho phép tất cả HTTP headers
        allow_headers=["*"],
        # Cho phép Frontend JS đọc các response headers tùy chỉnh
        expose_headers=["X-Total-Count", "X-Request-Id"],
        # Cache preflight response 10 phút — giảm số lượng OPTIONS request
        max_age=600,
    )

