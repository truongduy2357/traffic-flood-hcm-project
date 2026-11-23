"""
Endpoint cung cấp cấu hình công khai và giới hạn viewport TP.HCM cho Frontend (Task 3 & Task 19).
"""
from fastapi import APIRouter, status
from ..core.config import is_tomtom_api_key_configured, settings

router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin cấu hình hệ thống và ranh giới viewport TP.HCM",
    response_description="Tọa độ giới hạn TP.HCM, cấu hình bản đồ và cờ giao thông",
    responses={
        200: {
            "description": "Lấy cấu hình hệ thống thành công",
            "content": {
                "application/json": {
                    "example": {
                        "app_name": "Hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM",
                        "map_provider": "openfreemap",
                        "openfreemap_style_url": "https://tiles.openfreemap.org/styles/liberty",
                        "traffic_available": is_tomtom_api_key_configured(),
                        "hcm_bounds": {
                            "min_lat": 10.37,
                            "max_lat": 11.16,
                            "min_lng": 106.35,
                            "max_lng": 106.93
                        },
                        "hcm_center": {
                            "lat": 10.7769,
                            "lng": 106.7009
                        },
                        "rate_limit_per_minute": 60
                    }
                }
            }
        }
    }
)
def get_public_config():
    """
    Cung cấp cấu hình cần thiết để Frontend khởi tạo và khóa vùng bản đồ (SRS FR1.1):
    - **Ranh giới TP.HCM (Restrict Bounds):** Vĩ độ `10.37 - 11.16`, Kinh độ `106.35 - 106.93`.
    - **Tâm bản đồ mặc định:** `[106.7009, 10.7769]` (Khu vực trung tâm Quận 1).
    - **Thông số phân quyền:** Giới hạn tốc độ gọi API (Rate limit).
    """
    return {
        "app_name": settings.APP_NAME,
        "app_version": "1.0.0",
        "map_provider": "openfreemap",
        "openfreemap_style_url": "https://tiles.openfreemap.org/styles/liberty",
        "traffic_available": is_tomtom_api_key_configured(),
        "hcm_bounds": {
            "min_lat": settings.TPHCM_MIN_LAT,
            "max_lat": settings.TPHCM_MAX_LAT,
            "min_lng": settings.TPHCM_MIN_LNG,
            "max_lng": settings.TPHCM_MAX_LNG,
        },
        "maplibre_max_bounds": [
            [settings.TPHCM_MIN_LNG, settings.TPHCM_MIN_LAT],
            [settings.TPHCM_MAX_LNG, settings.TPHCM_MAX_LAT],
        ],
        "hcm_center": {
            "lat": 10.7769,
            "lng": 106.7009,
        },
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
    }
