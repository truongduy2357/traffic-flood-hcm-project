from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional, List
import sqlalchemy as sa
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Boolean,
    Enum,
    Index,
    func,
)

from app.db.session import Base
from app.models.spatial import Point, create_point_wkt, parse_point_wkt


class SeverityLevel(str, PyEnum):
    """
    Cấp độ ngập lụt theo đặc tả SRS:
    - low: Mắt cá chân (~10 - 20cm)
    - medium: Nửa bánh xe (~20 - 40cm)
    - high: Lút bánh xe (> 40cm)
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FloodReport(Base):
    """
    SQLAlchemy Model đại diện cho bảng 'flood_reports'.
    
    Yêu cầu đặc tả SRS (Mục 3.4 & Tasks 7, 8, 9):
    - id: INT (Primary Key, Auto Increment)
    - location: POINT SRID 4326 (Bắt buộc dùng chuẩn GPS 4326, NOT NULL)
    - severity_level: ENUM('low', 'medium', 'high')
    - reported_at: DATETIME DEFAULT CURRENT_TIMESTAMP
    - is_verified: BOOLEAN DEFAULT FALSE
    - expires_at: DATETIME NULL
    - SPATIAL INDEX bắt buộc trên cột location để tối ưu tốc độ truy vấn không gian.
    """
    __tablename__ = "flood_reports"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Khóa chính tự tăng của báo cáo ngập",
    )

    # Cột location kiểu POINT SRID 4326 (Bắt buộc NOT NULL để tạo SPATIAL INDEX trong MySQL)
    location = Column(
        Point(srid=4326),
        nullable=False,
        comment="Tọa độ GPS điểm ngập kiểu POINT SRID 4326 (WGS 84: lat lng)",
    )

    severity_level = Column(
        Enum(
            SeverityLevel,
            values_callable=lambda x: [e.value for e in x],
            name="flood_severity_enum",
        ),
        nullable=False,
        default=SeverityLevel.LOW,
        comment="Mức độ ngập: low (mắt cá chân), medium (nửa bánh xe), high (lút bánh xe)",
    )

    reported_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Thời điểm gửi báo cáo ngập",
    )

    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("0"),
        comment="Trạng thái xác minh bởi quản trị viên (Admin)",
    )

    expires_at = Column(
        DateTime,
        nullable=True,
        comment="Thời điểm tự động hạ cấp độ hoặc xóa điểm ngập khi hết hạn",
    )

    # Cấu hình bắt buộc SPATIAL INDEX trên cột location
    __table_args__ = (
        Index("idx_flood_reports_location", "location", mysql_prefix="SPATIAL"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
            "comment": "Bảng lưu trữ thông tin các điểm ngập lụt tại TP.HCM kèm tọa độ không gian",
        },
    )

    # --------------------------------------------------------------------------
    # Helper properties & methods hỗ trợ chuyển đổi dữ liệu không gian
    # --------------------------------------------------------------------------
    @property
    def latitude(self) -> Optional[float]:
        """Lấy giá trị Vĩ độ (Latitude) từ cột POINT location."""
        lat, _ = parse_point_wkt(self.location)
        return lat

    @property
    def longitude(self) -> Optional[float]:
        """Lấy giá trị Kinh độ (Longitude) từ cột POINT location."""
        _, lng = parse_point_wkt(self.location)
        return lng

    @property
    def coordinates(self) -> List[float]:
        """
        Chuyển đổi dữ liệu POINT SRID 4326 thành danh sách tọa độ [lat, lng]
        chuẩn để gửi về Frontend (phục vụ Task 28 trong SRS).
        """
        lat, lng = parse_point_wkt(self.location)
        if lat is not None and lng is not None:
            return [lat, lng]
        return []

    def set_coordinates(self, lat: float, lng: float) -> None:
        """Thiết lập tọa độ điểm ngập từ vĩ độ và kinh độ (POINT(lat lng))."""
        self.location = create_point_wkt(lat, lng)

    def __repr__(self) -> str:
        return (
            f"<FloodReport(id={self.id}, severity='{self.severity_level}', "
            f"location='{self.location}', is_verified={self.is_verified})>"
        )

