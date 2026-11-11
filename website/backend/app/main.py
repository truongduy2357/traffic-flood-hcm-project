"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM                    ║
║  FastAPI Application Entry Point (main.py)                                 ║
║                                                                            ║
║  Cấu hình bao gồm:                                                        ║
║  • CORS Middleware — cho phép trình duyệt (Chrome, Safari, Firefox) gọi   ║
║    API Backend không bị chặn bởi Same-Origin Policy (Task 15 SRS)          ║
║  • Startup Event — tự động khởi tạo database & SPATIAL INDEX               ║
║  • Health Check Endpoint — kiểm tra trạng thái server                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


# ==============================================================================
#  KHỞI TẠO ỨNG DỤNG FASTAPI
# ==============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "REST API hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM. "
        "Hỗ trợ truy vấn không gian (Spatial Query) trên MySQL 8.0+ với SRID 4326."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ==============================================================================
#  CẤU HÌNH CORS MIDDLEWARE (Task 15 — SRS mục 2.1 & 3.1)
# ==============================================================================
#
#  Cross-Origin Resource Sharing (CORS) cho phép trình duyệt web hiện đại
#  (Chrome, Safari, Firefox, Edge) gọi API Backend từ một domain/port khác
#  mà không bị chặn bởi Same-Origin Policy.
#
#  Giải thích các tham số:
#  ┌──────────────────────┬────────────────────────────────────────────────────┐
#  │ allow_origins        │ Danh sách domain Frontend được phép gọi API.     │
#  │                      │ Đọc từ biến CORS_ORIGINS trong file .env.        │
#  │                      │ Ví dụ: http://localhost:5500, http://localhost    │
#  ├──────────────────────┼────────────────────────────────────────────────────┤
#  │ allow_credentials    │ Cho phép gửi cookie/token xác thực cross-origin. │
#  │                      │ Cần thiết nếu Frontend dùng JWT trong cookie.    │
#  ├──────────────────────┼────────────────────────────────────────────────────┤
#  │ allow_methods        │ Các HTTP method được phép: GET, POST, PUT,       │
#  │                      │ DELETE, PATCH, OPTIONS (preflight).              │
#  ├──────────────────────┼────────────────────────────────────────────────────┤
#  │ allow_headers        │ Các HTTP header được phép gửi kèm request.       │
#  │                      │ ["*"] = chấp nhận tất cả headers.               │
#  ├──────────────────────┼────────────────────────────────────────────────────┤
#  │ expose_headers       │ Các header trong response mà JS được phép đọc.   │
#  │                      │ Mặc định browser ẩn header tùy chỉnh.           │
#  ├──────────────────────┼────────────────────────────────────────────────────┤
#  │ max_age              │ Thời gian cache kết quả preflight OPTIONS (giây).│
#  │                      │ 600s = 10 phút, giảm số lần preflight request.  │
#  └──────────────────────┴────────────────────────────────────────────────────┘
#
#  Luồng CORS hoạt động:
#  ┌─────────┐   OPTIONS (preflight)    ┌─────────┐
#  │ Browser │ ─────────────────────►   │ FastAPI │
#  │ (JS)    │   Origin: localhost:5500 │ Server  │
#  │         │ ◄─────────────────────   │         │
#  │         │   Access-Control-Allow-  │         │
#  │         │   Origin: localhost:5500 │         │
#  │         │                          │         │
#  │         │   GET/POST (actual)      │         │
#  │         │ ─────────────────────►   │         │
#  │         │ ◄─────────────────────   │         │
#  │         │   200 OK + JSON data     │         │
#  └─────────┘                          └─────────┘
# ==============================================================================

# Xử lý CORS_ORIGINS từ config: hỗ trợ cả list và string "*"
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [cors_origins]

app.add_middleware(
    CORSMiddleware,
    # Danh sách origin (domain) Frontend được phép truy cập API
    allow_origins=cors_origins,
    # Cho phép gửi credentials (cookies, Authorization header) cross-origin
    allow_credentials=True,
    # Cho phép tất cả HTTP methods (GET, POST, PUT, DELETE, PATCH, OPTIONS)
    allow_methods=["*"],
    # Cho phép tất cả HTTP headers (Content-Type, Authorization, X-Requested-With, ...)
    allow_headers=["*"],
    # Cho phép Frontend JS đọc các response headers tùy chỉnh
    expose_headers=["X-Total-Count", "X-Request-Id"],
    # Cache preflight response 10 phút — giảm số lượng OPTIONS request
    max_age=600,
)


# ==============================================================================
#  STARTUP EVENT — Khởi tạo Database & Spatial Index khi server khởi động
# ==============================================================================

@app.on_event("startup")
async def on_startup():
    """
    Khi FastAPI server khởi động:
    1. Tự động tạo bảng flood_reports nếu chưa tồn tại.
    2. Đảm bảo SPATIAL INDEX trên cột location đã được thiết lập.
    """
    try:
        from app.db.init_db import init_db
        init_db()
        print(f"[STARTUP] Database '{settings.DB_NAME}' & Spatial Index đã sẵn sàng.")
    except Exception as e:
        print(f"[STARTUP WARNING] Không thể khởi tạo database tự động: {e}")
        print(f"  → Hãy chạy migration thủ công: migrations/001_create_flood_reports.sql")


# ==============================================================================
#  HEALTH CHECK ENDPOINT (Task 14)
# ==============================================================================

@app.get(
    "/health",
    tags=["System"],
    summary="Kiểm tra trạng thái hoạt động của Backend Server",
    response_description="Trả về trạng thái OK nếu server đang hoạt động bình thường",
)
async def health_check():
    """
    API Health Check — Kiểm tra server sống/chết.

    Trả về:
    - **status**: "ok" nếu server đang hoạt động
    - **app_name**: Tên hệ thống
    - **environment**: Môi trường (development/production)
    """
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# ==============================================================================
#  ROOT ENDPOINT
# ==============================================================================

@app.get(
    "/",
    tags=["System"],
    summary="Trang chủ API",
)
async def root():
    """Endpoint gốc — Thông tin cơ bản về hệ thống API."""
    return {
        "message": "Hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM",
        "docs": "/docs",
        "health": "/health",
    }

