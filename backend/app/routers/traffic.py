"""Proxy TomTom traffic-flow tiles without exposing the API key to the browser."""
import urllib.request
import urllib.error
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response

from ..core.config import settings
from ..core.logger import app_logger

router = APIRouter(prefix="/api/v1/traffic", tags=["Traffic"])


@router.get("/flow/{z}/{x}/{y}.png", summary="Lấy tile giao thông TomTom")
async def get_traffic_flow_tile(
    z: int = Path(ge=0, le=22),
    x: int = Path(ge=0),
    y: int = Path(ge=0),
):
    tomtom_key = getattr(settings, "TOMTOM_API_KEY", None)
    if not tomtom_key:
        raise HTTPException(
            status_code=503,
            detail="Lớp giao thông chưa được cấu hình TOMTOM_API_KEY.",
        )

    tile_count = 1 << z
    if x >= tile_count or y >= tile_count:
        raise HTTPException(status_code=404, detail="Tile giao thông không hợp lệ.")

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
        raise HTTPException(status_code=502, detail="Không thể kết nối dịch vụ giao thông TomTom.")
