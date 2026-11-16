from datetime import datetime
from pydantic import BaseModel, Field
from app.models.flood_report import SeverityLevel
from app.core.config import settings


# 1. Schema gốc: Các thông tin cơ bản của điểm ngập (Ràng buộc phạm vi TP.HCM)
class FloodReportBase(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Tên tuyến đường hoặc khu vực ngập",
        examples=["Đường Nguyễn Hữu Cảnh, Bình Thạnh"],
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Mô tả chi tiết tình trạng ngập (tùy chọn)",
        examples=["Nước ngập nửa bánh xe, xe máy di chuyển khó khăn"],
    )
    latitude: float = Field(
        ...,
        ge=settings.TPHCM_MIN_LAT,  # 10.37
        le=settings.TPHCM_MAX_LAT,  # 11.16
        description=f"Vĩ độ GPS nằm trong phạm vi TP.HCM ({settings.TPHCM_MIN_LAT} đến {settings.TPHCM_MAX_LAT})",
        examples=[10.776889],
    )
    longitude: float = Field(
        ...,
        ge=settings.TPHCM_MIN_LNG,  # 106.35
        le=settings.TPHCM_MAX_LNG,  # 106.93
        description=f"Kinh độ GPS nằm trong phạm vi TP.HCM ({settings.TPHCM_MIN_LNG} đến {settings.TPHCM_MAX_LNG})",
        examples=[106.700806],
    )
    severity_level: SeverityLevel = Field(
        default=SeverityLevel.LOW,
        description="Mức độ ngập: low (mắt cá), medium (nửa bánh xe), high (lút bánh xe)",
    )
    water_depth_cm: int | None = Field(
        default=None,
        ge=0,
        le=300,
        description="Độ sâu ước lượng của mực nước (cm)",
        examples=[30],
    )
    radius_meters: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="Bán kính vùng ngập ảnh hưởng (mét)",
        examples=[50],
    )


# 2. Schema khi tạo mới (POST API): Người dân gửi báo cáo lên
class FloodReportCreate(FloodReportBase):
    is_verified: bool = False
    expires_at: datetime | None = None


# 3. Schema khi cập nhật (PUT / PATCH API): Cho phép sửa từng trường
class FloodReportUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    latitude: float | None = Field(default=None, ge=settings.TPHCM_MIN_LAT, le=settings.TPHCM_MAX_LAT)
    longitude: float | None = Field(default=None, ge=settings.TPHCM_MIN_LNG, le=settings.TPHCM_MAX_LNG)
    severity_level: SeverityLevel | None = None
    water_depth_cm: int | None = None
    radius_meters: int | None = None
    is_verified: bool | None = None
    expires_at: datetime | None = None


# 4. Schema khi trả về cho Frontend (GET API): Hiển thị lên bản đồ
class FloodReportResponse(FloodReportBase):
    id: int = Field(..., description="Mã định danh duy nhất của điểm ngập")
    reported_at: datetime = Field(..., description="Thời điểm gửi báo cáo")
    is_verified: bool = Field(default=False, description="Đã được quản trị viên duyệt hay chưa")
    expires_at: datetime | None = None
    coordinates: list[float] | None = None

    class Config:
        from_attributes = True
