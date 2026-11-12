from datetime import datetime
from pydantic import BaseModel, Field
from app.models.flood_report import SeverityLevel


# 1. Schema gốc: Các thông tin cơ bản của điểm ngập
class FloodReportBase(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vĩ độ GPS (-90 đến 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Kinh độ GPS (-180 đến 180)")
    severity_level: SeverityLevel = SeverityLevel.LOW


# 2. Schema khi tạo mới (POST API): Người dân gửi báo cáo lên
class FloodReportCreate(FloodReportBase):
    is_verified: bool = False
    expires_at: datetime | None = None


# 3. Schema khi cập nhật (PUT / PATCH API): Cho phép sửa từng trường
class FloodReportUpdate(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    severity_level: SeverityLevel | None = None
    is_verified: bool | None = None
    expires_at: datetime | None = None


# 4. Schema khi trả về cho Frontend (GET API): Hiển thị lên bản đồ
class FloodReportResponse(FloodReportBase):
    id: int
    reported_at: datetime
    is_verified: bool
    expires_at: datetime | None = None
    coordinates: list[float] | None = None

    class Config:
        from_attributes = True