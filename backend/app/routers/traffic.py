"""Proxy TomTom traffic-flow tiles without exposing the API key to the browser."""
import urllib.request
import urllib.error
from fastapi import APIRouter, HTTPException, Path, status
from fastapi.responses import Response

from ..core.config import settings
from ..core.logger import app_logger

router = APIRouter(prefix="/api/v1/traffic", tags=["Traffic"])


@router.get(
    "/flow/{z}/{x}/{y}.png",
    status_code=status.HTTP_200_OK,
    summary="Lấy tile bản đồ mật độ giao thông theo thời gian thực (Traffic Flow Tile)",
    response_description="Hình ảnh raster tile PNG biểu thị mật độ kẹt xe",
    responses={
        200: {
            "description": "Trả về dữ liệu hình ảnh tile PNG",
            "content": {"image/png": {}}
        },
        404: {"description": "Chỉ số tọa độ tile không hợp lệ trên hệ thống phóng to thu nhỏ"},
        502: {"description": "Lỗi kết nối tới nhà cung cấp dữ liệu giao thông vệ tinh"},
        503: {"description": "Dịch vụ giao thông chưa được kích hoạt khóa API Key"}
    }
)
async def get_traffic_flow_tile(
    z: int = Path(..., ge=0, le=22, description="Cấp độ thu phóng (Zoom level: 0 - 22)"),
    x: int = Path(..., ge=0, description="Tọa độ cột x của tile"),
    y: int = Path(..., ge=0, description="Tọa độ hàng y của tile"),
):
    """
    Proxy bảo mật tải các mảnh bản đồ (tile) giao thông thời gian thực:
    - Bảo vệ khóa API Key phía máy chủ, không lộ ra trình duyệt.
    - Tự động cache tile trong 60 giây để tối ưu tốc độ và giảm lưu lượng mạng.
    """
    tomtom_key = getattr(settings, "TOMTOM_API_KEY", None)
    if not tomtom_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lớp giao thông chưa được cấu hình TOMTOM_API_KEY.",
        )

    tile_count = 1 << z
    if x >= tile_count or y >= tile_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tile giao thông không hợp lệ.")

    url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png?key={tomtom_key}&tileSize=256"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FastAPI-Backend"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            content = resp.read()
            return Response(
                content=content,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=60"},
            )
    except urllib.error.HTTPError as exc:
        app_logger.warning(f"TomTom tile HTTP error: {exc.code}")
        raise HTTPException(status_code=exc.code, detail="Không tải được tile giao thông.")
    except Exception as exc:
        app_logger.warning(f"TomTom tile proxy error: {exc}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Không thể kết nối dịch vụ giao thông.")
