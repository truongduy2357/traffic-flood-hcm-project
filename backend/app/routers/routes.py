"""
API Kiểm tra lộ trình di chuyển và phát hiện điểm ngập (Task 39 & Task 40 - FR4 SRS)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.route import RouteCheckRequest, RouteCheckResponse
from ..services.route_service import RouteService

router = APIRouter(prefix="/api/v1/routes", tags=["Routes"])


@router.post(
    "/check-flood",
    response_model=RouteCheckResponse,
    summary="Kiểm tra giao cắt tuyến đường với các điểm ngập (ST_Intersects & ST_Distance_Sphere)",
)
def check_route(payload: RouteCheckRequest, db: Session = Depends(get_db)):
    """
    Nhận chuỗi Polyline mã hóa hoặc danh sách điểm từ Frontend (Google Directions API / OSRM):
    1. Giải mã chuỗi Polyline thành danh sách điểm tọa độ GPS và chuyển thành đối tượng LINESTRING (Task 39).
    2. Viết câu lệnh MySQL dùng hàm không gian ST_Intersects và ST_Distance_Sphere để kiểm tra lộ trình có cắt qua điểm ngập không (Task 40).
    3. Trả về kết quả phát hiện ngập, số lượng điểm ngập, mức độ nghiêm trọng và gợi ý cảnh báo.
    """
    points_dict = [pt.model_dump() for pt in payload.points] if payload.points else None
    result = RouteService.check_route_against_floods(
        db=db,
        encoded_polyline=payload.encoded_polyline,
        points=points_dict,
        buffer_meters=payload.buffer_meters,
    )
    return result
