
"""
HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
FastAPI Application Entry Point

Chức năng:
- Khởi tạo FastAPI application.
- Cấu hình hệ thống Logging.
- Theo dõi lịch sử truy cập API.
- Khởi tạo Database và Spatial Index.
- Đăng ký CORS, Rate Limiting.
- Xử lý ngoại lệ hệ thống.
"""

from fastapi import FastAPI

from app.core.config import settings
from app.core.handleExp import AppException, handle_app_exception
from app.core.logging_config import setup_logging, get_logger

from app.middleware.cors import setup_cors
from app.middleware.rate_limiter import setup_rate_limiting
from app.middleware.request_logging import setup_request_logging


# ============================================================
# 1. KHỞI TẠO HỆ THỐNG LOGGING
# ============================================================

# Thiết lập ghi log ra file và terminal
setup_logging()

# Logger dành cho module main
logger = get_logger("main")


# ============================================================
# 2. KHỞI TẠO FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "REST API hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM. "
        "Hỗ trợ truy vấn không gian (Spatial Query) trên MySQL 8.0+ "
        "với SRID 4326."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# 3. ĐĂNG KÝ MIDDLEWARE
# ============================================================

# Theo dõi lịch sử truy cập API:
# IP, HTTP Method, Endpoint, Status Code, Response Time
setup_request_logging(app)

# Cấu hình CORS cho phép Frontend truy cập Backend
setup_cors(app)

# Rate Limiting chống spam các endpoint nhạy cảm
setup_rate_limiting(app)


# ============================================================
# 4. ĐĂNG KÝ XỬ LÝ NGOẠI LỆ
# ============================================================

app.add_exception_handler(
    AppException,
    handle_app_exception,
)


# ============================================================
# 5. SỰ KIỆN KHỞI ĐỘNG HỆ THỐNG
# ============================================================

@app.on_event("startup")
async def on_startup():
    """
    Khởi tạo Database và Spatial Index khi Backend khởi động.
    Ghi log trạng thái khởi động và lỗi nếu có.
    """

    logger.info("Đang khởi động hệ thống %s...", settings.APP_NAME)

    try:
        from app.db.init_db import init_db

        # Khởi tạo các bảng Database và Spatial Index
        init_db()

        logger.info(
            "Database '%s' và Spatial Index đã sẵn sàng.",
            settings.DB_NAME,
        )

    except Exception:
        # Ghi lại lỗi kèm traceback
        logger.exception(
            "Không thể khởi tạo Database '%s'.",
            settings.DB_NAME,
        )

    logger.info("Hệ thống FastAPI đã khởi động.")


# ============================================================
# 6. API HEALTH CHECK
# ============================================================

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
)
async def health_check():
    """
    Kiểm tra trạng thái hoạt động của Backend.
    """

    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# ============================================================
# 7. API SYSTEM CONFIGURATION
# ============================================================

@app.get(
    "/api/v1/config",
    tags=["System"],
    summary="Cấu hình hệ thống và giới hạn viewport TP.HCM",
)
async def get_system_config():
    """
    Trả về cấu hình hệ thống và ranh giới viewport TP.HCM.

    Vĩ độ: 10.37 đến 11.16
    Kinh độ: 106.35 đến 106.93
    """

    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "openfreemap_style_url": (
            "https://tiles.openfreemap.org/styles/liberty"
        ),
        "traffic_available": False,

        "hcm_bounds": {
            "min_lat": settings.TPHCM_MIN_LAT,
            "max_lat": settings.TPHCM_MAX_LAT,
            "min_lng": settings.TPHCM_MIN_LNG,
            "max_lng": settings.TPHCM_MAX_LNG,
        },

        "maplibre_max_bounds": [
            [
                settings.TPHCM_MIN_LNG,
                settings.TPHCM_MIN_LAT,
            ],
            [
                settings.TPHCM_MAX_LNG,
                settings.TPHCM_MAX_LAT,
            ],
        ],

        "hcm_center": [106.7009, 10.7769],
    }


# ============================================================
# 8. API ROOT
# ============================================================

@app.get(
    "/",
    tags=["System"],
    summary="Trang chủ API",
)
async def root():
    """
    Trả về thông tin cơ bản của hệ thống API.
    """

    return {
        "message": settings.APP_NAME,
        "docs": "/docs",
        "health": "/health",
    }
