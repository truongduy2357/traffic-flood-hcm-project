"""
Pydantic Schemas cho API kiểm tra tuyến đường né ngập (Routing & Spatial Intersect).
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CoordinatePoint(BaseModel):
    """Tọa độ GPS một điểm trên tuyến đường."""
    latitude: float = Field(..., ge=-90, le=90, description="Vĩ độ (Latitude)")
    longitude: float = Field(..., ge=-180, le=180, description="Kinh độ (Longitude)")


class RouteCheckRequest(BaseModel):
    """
    Dữ liệu yêu cầu kiểm tra lộ trình từ Frontend:
    - encoded_polyline: Chuỗi Polyline mã hóa sinh ra từ Google Directions API hoặc OSRM.
    - points: Hoặc danh sách các tọa độ điểm [lat, lng] chi tiết.
    - buffer_meters: Bán kính vùng đệm an toàn quanh tuyến đường (mặc định 50m).
    """
    encoded_polyline: Optional[str] = Field(
        None,
        description="Chuỗi Polyline mã hóa của tuyến đường (Google Directions API / OSRM)"
    )
    points: Optional[List[CoordinatePoint]] = Field(
        None,
        description="Danh sách tọa độ các điểm trên tuyến đường"
    )
    buffer_meters: float = Field(
        default=50.0,
        ge=0.0,
        le=500.0,
        description="Bán kính kiểm tra ngập xung quanh tuyến đường (mét)"
    )


class FloodIntersection(BaseModel):
    """Thông tin chi tiết điểm ngập nằm trên hoặc gần tuyến đường."""
    id: int
    severity_level: str
    latitude: float
    longitude: float
    distance_to_route_meters: float
    is_verified: bool
    reported_at: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None


class RouteCheckResponse(BaseModel):
    """
    Kết quả kiểm tra không gian lộ trình né ngập:
    - has_flood: Tuyến đường có đi qua vùng ngập hay không.
    - intercepted_count: Số điểm ngập bị giao cắt hoặc nằm trong bán kính ảnh hưởng.
    - max_severity: Cấp độ ngập nặng nhất phát hiện được (low, medium, high).
    - warning_message: Thông điệp cảnh báo hiển thị cho người dùng.
    - floods: Danh sách các điểm ngập chi tiết.
    - linestring_wkt: Chuỗi WKT LINESTRING đã được giải mã.
    - total_points: Số lượng điểm tọa độ cấu thành tuyến đường.
    """
    has_flood: bool
    intercepted_count: int
    max_severity: Optional[str] = None
    warning_message: str
    floods: List[FloodIntersection] = []
    linestring_wkt: Optional[str] = None
    total_points: int = 0
