"""
API Kiểm tra lộ trình di chuyển và phát hiện điểm ngập (Task 39 & Task 40 - FR4 SRS)
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.route import RouteCheckRequest, RouteCheckResponse
from ..services.route_service import RouteService

router = APIRouter(prefix="/api/v1/routes", tags=["Routes"])


@router.post(
    "/check-flood",
    response_model=RouteCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Kiểm tra tuyến đường có cắt qua điểm ngập không (ST_Intersects & ST_Distance_Sphere)",
    response_description="Kết quả phân tích không gian: Cảnh báo nguy cơ ngập, số điểm ngập giao cắt và danh sách chi tiết",
    responses={
        200: {
            "description": "Phân tích không gian lộ trình thành công",
            "content": {
                "application/json": {
                    "example": {
                        "has_flood": True,
                        "intercepted_count": 1,
                        "max_severity": "high",
                        "warning_message": "CẢNH BÁO: Phát hiện 1 điểm ngập trên lộ trình! Mức độ: HIGH. Bạn nên chọn lộ trình né ngập an toàn.",
                        "floods": [
                            {
                                "id": 1,
                                "severity_level": "high",
                                "latitude": 10.7932,
                                "longitude": 106.7214,
                                "distance_to_route_meters": 12.5,
                                "is_verified": True,
                                "reported_at": "2026-11-23T08:00:00",
                                "title": "Điểm ngập #1",
                                "description": "Khoảng cách tới lộ trình: 12.5 mét. Mức độ: high."
                            }
                        ],
                        "linestring_wkt": "LINESTRING(10.772500 106.698000, 10.785000 106.705000...)",
                        "total_points": 45
                    }
                }
            }
        },
        400: {"description": "Dữ liệu polyline hoặc danh sách điểm tọa độ không hợp lệ"},
        500: {"description": "Lỗi máy chủ khi thực thi truy vấn không gian MySQL"}
    }
)
def check_route(payload: RouteCheckRequest, db: Session = Depends(get_db)):
    """
    Phân tích không gian tuyến đường và cảnh báo né ngập (SRS FR4.2):
    - **Bước 1 (Task 39):** Nhận chuỗi `encoded_polyline` từ Frontend (Google Directions / OSRM) và giải mã thành đối tượng hình học `LINESTRING` chuẩn GPS SRID 4326.
    - **Bước 2 (Task 40):** Thực thi câu lệnh SQL sử dụng các hàm không gian MySQL:
      - `ST_Intersects`: Phát hiện giao cắt trực tiếp giữa lộ trình và vùng ngập.
      - `ST_Distance_Sphere`: Tính khoảng cách cong thực tế trên mặt cầu Trái Đất (mét) giữa tuyến đường và điểm ngập, so sánh với `buffer_meters`.
    - **Bước 3:** Trả về kết quả cảnh báo mức độ ngập (`low`, `medium`, `high`) để Frontend đổi màu lộ trình hoặc tự động đề xuất tuyến đường tránh an toàn.
    """
    points_dict = [pt.model_dump() for pt in payload.points] if payload.points else None
    result = RouteService.check_route_against_floods(
        db=db,
        encoded_polyline=payload.encoded_polyline,
        points=points_dict,
        buffer_meters=payload.buffer_meters,
    )
    return result
