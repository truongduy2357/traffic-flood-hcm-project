
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

from datetime import datetime
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.handleExp import AppException, handle_app_exception
from app.core.logging_config import setup_logging, get_logger

from app.db.session import get_db
from app.models.flood_report import FloodReport

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

    # Khởi động Task chạy ngầm tự động hạ cấp / xóa điểm ngập hết hạn (Sprint 3)
    try:
        import asyncio
        from app.core.flood_cleanup import start_flood_cleanup_background_task
        asyncio.create_task(start_flood_cleanup_background_task(interval_seconds=60))
        logger.info("Background Task dọn dẹp điểm ngập định kỳ đã được kích hoạt.")
    except Exception as e:
        logger.warning("Không thể kích hoạt Background Task dọn dẹp điểm ngập: %s", e)

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
# 8. API FLOODS (Sprint 3) - TRUY VẤN DANH SÁCH ĐIỂM NGẬP ĐANG HOẠT ĐỘNG
# ============================================================

@app.get(
    "/api/v1/floods",
    tags=["Floods"],
    summary="Lấy danh sách điểm ngập đang hoạt động từ CSDL MySQL",
)
@app.get(
    "/floods",
    tags=["Floods"],
    summary="Lấy danh sách điểm ngập đang hoạt động (Đường dẫn rút gọn)",
)
def get_active_floods(db: Session = Depends(get_db)):
    """
    Truy vấn danh sách các điểm ngập đang hoạt động từ CSDL MySQL.
    - Điều kiện: expires_at IS NULL hoặc expires_at > NOW() (chưa hết hạn).
    - Trả về: Danh sách JSON điểm ngập gồm tọa độ GPS, mức độ ngập và bán kính.
    """
    try:
        now = datetime.now()
        # Truy vấn các điểm ngập còn hiệu lực từ CSDL MySQL
        active_reports = (
            db.query(FloodReport)
            .filter(
                or_(
                    FloodReport.expires_at.is_(None),
                    FloodReport.expires_at > now,
                )
            )
            .order_by(FloodReport.reported_at.desc())
            .all()
        )

        results = []
        for r in active_reports:
            lat = r.latitude
            lng = r.longitude
            if lat is not None and lng is not None:
                sev_val = r.severity_level.value if hasattr(r.severity_level, "value") else str(r.severity_level)
                depth = 45 if sev_val == "high" else (30 if sev_val == "medium" else 15)
                results.append({
                    "id": r.id,
                    "title": f"Điểm ngập #{r.id}",
                    "description": f"Mức độ: {sev_val}",
                    "latitude": lat,
                    "longitude": lng,
                    "severity_level": sev_val,
                    "water_depth_cm": depth,
                    "radius_meters": 60 if sev_val == "high" else 50,
                    "is_verified": bool(r.is_verified),
                    "reported_at": r.reported_at.isoformat() if r.reported_at else now.isoformat(),
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                })

        return results

    except Exception as e:
        logger.warning("Không thể truy vấn CSDL MySQL, trả về danh sách mẫu dự phòng: %s", e)
        # Dữ liệu mẫu dự phòng tại TP.HCM (đảm bảo sinh viên luôn test được frontend ngay cả khi chưa bật MySQL)
        return [
            {
                "id": 1,
                "title": "Đường Nguyễn Hữu Cảnh, Bình Thạnh",
                "description": "Ngập sâu đoạn chân cầu Thủ Thiêm, xe chết máy hàng loạt",
                "latitude": 10.7932,
                "longitude": 106.7214,
                "severity_level": "high",
                "water_depth_cm": 45,
                "radius_meters": 80,
                "is_verified": True,
                "reported_at": datetime.now().isoformat(),
            },
            {
                "id": 2,
                "title": "Đường Huỳnh Tấn Phát, Quận 7",
                "description": "Triều cường dâng cao ngập nửa bánh xe",
                "latitude": 10.7428,
                "longitude": 106.7325,
                "severity_level": "medium",
                "water_depth_cm": 30,
                "radius_meters": 60,
                "is_verified": True,
                "reported_at": datetime.now().isoformat(),
            },
            {
                "id": 3,
                "title": "Đường Quốc Hương, Thảo Điền",
                "description": "Nước ngập mắt cá chân, các phương tiện di chuyển chậm",
                "latitude": 10.8045,
                "longitude": 106.7321,
                "severity_level": "low",
                "water_depth_cm": 15,
                "radius_meters": 40,
                "is_verified": False,
                "reported_at": datetime.now().isoformat(),
            },
        ]


@app.post(
    "/api/v1/floods/cleanup",
    tags=["Floods"],
    summary="Kích hoạt thủ công tác vụ hạ cấp hoặc xóa điểm ngập hết hạn",
)
@app.post(
    "/floods/cleanup",
    tags=["Floods"],
    summary="Kích hoạt thủ công tác vụ dọn dẹp điểm ngập (Đường dẫn rút gọn)",
)
def trigger_flood_cleanup(db: Session = Depends(get_db)):
    """
    Cho phép quản trị viên hoặc kiểm thử kích hoạt ngay lập tức
    tiến trình hạ cấp độ hoặc xóa các điểm ngập đã quá hạn expires_at
    mà chưa có xác thực thêm.
    """
    from app.core.flood_cleanup import cleanup_expired_flood_reports
    return cleanup_expired_flood_reports(db)


# ============================================================
# 9. API ROOT
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
