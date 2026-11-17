"""
API Kiểm tra lộ trình di chuyển và phát hiện điểm ngập (Né ngập thông minh)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.route import RouteCheckRequest, RouteCheckResponse
from ..services.flood_service import FloodService

router = APIRouter(prefix="/api/v1/routes", tags=["Routes"])

@router.post("/check-flood", response_model=RouteCheckResponse, summary="Kiểm tra giao cắt tuyến đường với các điểm ngập")
def check_route(payload: RouteCheckRequest, db: Session = Depends(get_db)):
    """
    Nhận chuỗi Polyline mã hóa hoặc danh sách điểm từ Google Directions API:
    - Giải mã Polyline thành chuỗi tọa độ (LINESTRING)
    - So sánh với các điểm ngập trong bán kính ảnh hưởng (MySQL ST_Distance_Sphere / Spatial Query)
    - Trả về cảnh báo màu sắc và đề xuất điều hướng an toàn
    """
    points_dict = [pt.model_dump() for pt in payload.points] if payload.points else None
    result = FloodService.check_route_against_floods(
        db=db,
        encoded_polyline=payload.encoded_polyline,
        points=points_dict,
        buffer_meters=payload.buffer_meters
    )
    return result
