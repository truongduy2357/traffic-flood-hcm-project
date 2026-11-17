"""Proxy TomTom traffic-flow tiles without exposing the API key to the browser."""
import httpx
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
    if not settings.TOMTOM_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Lớp giao thông chưa được cấu hình TOMTOM_API_KEY.",
        )

    tile_count = 1 << z
    if x >= tile_count or y >= tile_count:
        raise HTTPException(status_code=404, detail="Tile giao thông không hợp lệ.")

    url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.get(url, params={"key": settings.TOMTOM_API_KEY})
    except httpx.HTTPError as exc:
        app_logger.warning(
            "Không thể tải tile giao thông TomTom (%s).",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="Không thể kết nối dịch vụ giao thông TomTom.",
        ) from exc

    if upstream.status_code != 200:
        app_logger.warning(
            "TomTom trả về lỗi khi tải tile giao thông: HTTP %s",
            upstream.status_code,
        )
        raise HTTPException(
            status_code=502,
            detail="Dịch vụ giao thông TomTom không trả về tile hợp lệ.",
        )

    return Response(
        content=upstream.content,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=60"},
    )
