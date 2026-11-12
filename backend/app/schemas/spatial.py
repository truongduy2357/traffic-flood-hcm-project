from typing import Any
from pydantic import BaseModel, Field, model_validator


# 1. Tọa độ điểm đơn lẻ (WGS 84 - SRID 4326)
class PointCoordinate(BaseModel):
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Vĩ độ GPS theo chuẩn WGS 84 (TPHCM: 10.37 - 11.16)",
        examples=[10.776889],
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Kinh độ GPS theo chuẩn WGS 84 (TPHCM: 106.35 - 106.93)",
        examples=[106.700806],
    )


# 2. Truy vấn không gian theo Bán kính (Nearby / Buffer Query - ST_Distance_Sphere)
class NearbyQuery(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vĩ độ tâm tìm kiếm")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Kinh độ tâm tìm kiếm")
    radius_meters: float = Field(
        default=1000.0,
        gt=0.0,
        le=50000.0,
        description="Bán kính quét xung quanh tâm tính bằng mét (mặc định 1km, tối đa 50km)",
        examples=[1500.0],
    )


# 3. Truy vấn không gian theo Hộp giới hạn Viewport (Bounding Box / BBox Query - ST_Contains)
class BoundingBoxQuery(BaseModel):
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Vĩ độ góc Tây Nam")
    min_lng: float = Field(..., ge=-180.0, le=180.0, description="Kinh độ góc Tây Nam")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Vĩ độ góc Đông Bắc")
    max_lng: float = Field(..., ge=-180.0, le=180.0, description="Kinh độ góc Đông Bắc")

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.min_lat >= self.max_lat:
            raise ValueError("min_lat phải nhỏ hơn max_lat")
        if self.min_lng >= self.max_lng:
            raise ValueError("min_lng phải nhỏ hơn max_lng")
        return self


# 4. Schema Kiểm tra Tuyến đường giao cắt điểm ngập (SRS FR4 & Frontend routing.js)
class RouteCheckRequest(BaseModel):
    points: list[PointCoordinate] = Field(
        ...,
        min_length=2,
        description="Danh sách tọa độ các điểm trên lộ trình cần kiểm tra ngập lụt",
    )
    buffer_meters: float = Field(
        default=60.0,
        ge=5.0,
        le=500.0,
        description="Bán kính vùng đệm an toàn xung quanh tuyến đường (mét)",
        examples=[60.0],
    )


class InterceptedFloodItem(BaseModel):
    id: int | None = Field(default=None, description="ID của điểm ngập")
    title: str = Field(..., description="Tên đường / Khu vực ngập", examples=["Đường Nguyễn Hữu Cảnh"])
    severity_level: str = Field(..., description="Mức độ ngập: low, medium, high", examples=["high"])
    distance_to_route_meters: float = Field(
        ...,
        description="Khoảng cách từ điểm ngập đến lộ trình (mét)",
        examples=[25.4],
    )
    latitude: float = Field(..., description="Vĩ độ của điểm ngập")
    longitude: float = Field(..., description="Kinh độ của điểm ngập")


class RouteCheckResponse(BaseModel):
    is_safe: bool = Field(
        ...,
        description="True nếu tuyến đường an toàn, False nếu phát hiện điểm ngập",
    )
    warning_message: str = Field(
        ...,
        description="Thông báo tổng quan về mức độ ngập trên lộ trình",
        examples=["Phát hiện 2 điểm ngập nặng trên lộ trình di chuyển."],
    )
    suggested_action: str = Field(
        ...,
        description="Hành động gợi ý cho người tham gia giao thông",
        examples=["Khuyến cáo chuyển sang lộ trình né ngập thay thế."],
    )
    intercepted_floods: list[InterceptedFloodItem] = Field(
        default=[],
        description="Danh sách chi tiết các điểm ngập giao cắt hoặc nằm trong vùng đệm của tuyến đường",
    )


# 5. Schema Định dạng Chuẩn GeoJSON (Dành cho MapLibre GL JS / Leaflet / GIS)
class GeoJSONGeometry(BaseModel):
    type: str = Field(default="Point", description="Kiểu hình học GeoJSON (Point, LineString, Polygon)")
    coordinates: list[Any] = Field(..., description="Tọa độ hình học GeoJSON (chuẩn GeoJSON: [lng, lat])")


class GeoJSONFeature(BaseModel):
    type: str = Field(default="Feature", description="Loại Feature GeoJSON")
    geometry: GeoJSONGeometry
    properties: dict[str, Any] = Field(default_factory=dict, description="Thuộc tính đi kèm đối tượng không gian")


class GeoJSONFeatureCollection(BaseModel):
    type: str = Field(default="FeatureCollection", description="Tập hợp đối tượng FeatureCollection GeoJSON")
    features: list[GeoJSONFeature] = Field(default=[], description="Danh sách các đối tượng Feature")
