"""
Service quản lý dữ liệu điểm ngập lụt (CRUD & Spatial Queries).
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from app.models.flood_report import FloodReport, SeverityLevel
from app.models.spatial import create_point_wkt
from app.schemas.flood_report import FloodReportCreate, FloodReportUpdate
from app.services.route_service import RouteService
from app.core.config import settings
from app.core.logger import app_logger
from zoneinfo import ZoneInfo


class FloodService:
    @staticmethod
    def get_active_floods(db: Session) -> List[FloodReport]:
        """Lấy danh sách các điểm ngập còn hiệu lực (chưa hết hạn)."""
        now = datetime.now()
        return (
            db.query(FloodReport)
            .filter(or_(FloodReport.expires_at.is_(None), FloodReport.expires_at > now))
            .order_by(FloodReport.reported_at.desc())
            .all()
        )

    @staticmethod
    def get_all_floods(db: Session, limit: int = 100) -> List[FloodReport]:
        """Admin: Lấy danh sách toàn bộ các điểm ngập."""
        return db.query(FloodReport).order_by(FloodReport.reported_at.desc()).limit(limit).all()

    @staticmethod
    def create_report(db: Session, report_in: FloodReportCreate, client_ip: str = "127.0.0.1") -> FloodReport:
        """Tạo mới báo cáo điểm ngập với chuẩn POINT SRID 4326."""
        now = datetime.now()
        expires = report_in.expires_at

        # Chuyển thời gian UTC sang giờ Việt Nam trước khi lưu MySQL DATETIME
        if expires is not None and expires.tzinfo is not None:
            expires = expires.astimezone(
                ZoneInfo("Asia/Ho_Chi_Minh")
            ).replace(tzinfo=None)

        # Nếu không truyền expires_at thì tự động cộng thời gian hết hạn
        if expires is None:
            expires = now + timedelta(hours=settings.FLOOD_EXPIRATION_HOURS)

        point_wkt = create_point_wkt(report_in.latitude, report_in.longitude)

        # Chèn vào database sử dụng ST_GeomFromText chuẩn SRID 4326
        db_report = FloodReport(
            location=point_wkt,
            severity_level=report_in.severity_level,
            is_verified=report_in.is_verified,
            expires_at=expires,
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)

        app_logger.info(f"Đã tạo báo cáo ngập #{db_report.id} tại [{report_in.latitude}, {report_in.longitude}]")
        return db_report

    @staticmethod
    def verify_report(db: Session, flood_id: int) -> Optional[FloodReport]:
        """Admin duyệt xác minh điểm ngập."""
        report = db.query(FloodReport).filter(FloodReport.id == flood_id).first()
        if report:
            report.is_verified = True
            db.commit()
            db.refresh(report)
        return report

    @staticmethod
    def update_report(db: Session, flood_id: int, update_in: FloodReportUpdate) -> Optional[FloodReport]:
        """Admin cập nhật thông tin điểm ngập."""
        report = db.query(FloodReport).filter(FloodReport.id == flood_id).first()
        if not report:
            return None

        if update_in.severity_level is not None:
            report.severity_level = update_in.severity_level
        if update_in.is_verified is not None:
            report.is_verified = update_in.is_verified
        if update_in.expires_at is not None:
            report.expires_at = update_in.expires_at
        if update_in.latitude is not None and update_in.longitude is not None:
            report.location = create_point_wkt(update_in.latitude, update_in.longitude)

        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def delete_report(db: Session, flood_id: int) -> bool:
        """Admin xóa điểm ngập."""
        report = db.query(FloodReport).filter(FloodReport.id == flood_id).first()
        if not report:
            return False
        db.delete(report)
        db.commit()
        return True

    @staticmethod
    def check_route_against_floods(
        db: Session,
        encoded_polyline: Optional[str] = None,
        points: Optional[List[Dict[str, float]]] = None,
        buffer_meters: float = 50.0,
    ) -> Dict[str, Any]:
        """Gọi RouteService thực hiện giải mã Polyline sang LINESTRING và chạy ST_Intersects, ST_Distance_Sphere."""
        return RouteService.check_route_against_floods(
            db=db,
            encoded_polyline=encoded_polyline,
            points=points,
            buffer_meters=buffer_meters,
        )
