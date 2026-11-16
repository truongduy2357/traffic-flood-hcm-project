"""
HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from app.core.config import settings
from app.middleware.cors import setup_cors
from app.middleware.rate_limiter import setup_rate_limiting
from app.core.handleExp import AppException, handle_app_exception

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

# Đăng ký xử lý ngoại lệ tùy chỉnh
app.add_exception_handler(AppException, handle_app_exception)

# Gắn CORS — toàn bộ logic nằm trong app/middleware/cors.py
setup_cors(app)

# Gắn Rate Limiting chống spam các endpoint nhạy cảm (SRS)
setup_rate_limiting(app)


@app.on_event("startup")
async def on_startup():
    try:
        from app.db.init_db import init_db
        init_db()
        print(f"[STARTUP] Database '{settings.DB_NAME}' & Spatial Index đã sẵn sàng.")
    except Exception as e:
        print(f"[STARTUP WARNING] Không thể khởi tạo database tự động: {e}")


@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    return {"status": "ok", "app_name": settings.APP_NAME, "environment": settings.APP_ENV}


@app.get("/api/v1/config", tags=["System"], summary="Cấu hình hệ thống & Giới hạn viewport TP.HCM")
async def get_system_config():
    """
    Trả về cấu hình hệ thống và ranh giới viewport TP.HCM cho Frontend:
    Vĩ độ: 10.37 đến 11.16 | Kinh độ: 106.35 đến 106.93
    """
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "openfreemap_style_url": "https://tiles.openfreemap.org/styles/liberty",
        "traffic_available": False,
        "hcm_bounds": {
            "min_lat": settings.TPHCM_MIN_LAT,  # 10.37
            "max_lat": settings.TPHCM_MAX_LAT,  # 11.16
            "min_lng": settings.TPHCM_MIN_LNG,  # 106.35
            "max_lng": settings.TPHCM_MAX_LNG,  # 106.93
        },
        "maplibre_max_bounds": [
            [settings.TPHCM_MIN_LNG, settings.TPHCM_MIN_LAT],  # [106.35, 10.37] Tây Nam
            [settings.TPHCM_MAX_LNG, settings.TPHCM_MAX_LAT],  # [106.93, 11.16] Đông Bắc
        ],
        "hcm_center": [106.7009, 10.7769],
    }


@app.get("/", tags=["System"], summary="Trang chủ API")
async def root():
    return {"message": settings.APP_NAME, "docs": "/docs", "health": "/health"}
