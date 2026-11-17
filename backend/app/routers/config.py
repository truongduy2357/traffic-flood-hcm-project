"""
Endpoint cung cấp cấu hình an toàn cho Frontend (OpenFreeMap, HCM Bounds)
"""
from fastapi import APIRouter
from ..core.config import settings

router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])

@router.get("", summary="Lấy thông tin cấu hình phục vụ bản đồ OpenFreeMap")
def get_public_config():
    return {
        "map_provider": settings.MAP_PROVIDER,
        "openfreemap_style_url": settings.OPENFREEMAP_STYLE_URL,
        "requires_api_key": False,
        "traffic_available": bool(settings.TOMTOM_API_KEY),
        "hcm_bounds": {
            "lat_min": settings.HCM_BOUNDS_LAT_MIN,
            "lat_max": settings.HCM_BOUNDS_LAT_MAX,
            "lng_min": settings.HCM_BOUNDS_LNG_MIN,
            "lng_max": settings.HCM_BOUNDS_LNG_MAX,
        },
        "hcm_center": {
            "lat": settings.HCM_CENTER_LAT,
            "lng": settings.HCM_CENTER_LNG,
        },
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }
