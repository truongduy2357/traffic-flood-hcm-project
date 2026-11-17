"""
Module: flood_cleanup.py
Dự án: Bản đồ Cảnh báo Kẹt xe & Ngập lụt TPHCM
Mục đích (Sprint 3 - Task Background Job):
Viết task chạy ngầm tự động hạ cấp độ ngập hoặc xóa điểm ngập
sau thời gian expires_at nếu không có xác thực thêm.
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.flood_report import FloodReport, SeverityLevel
from app.core.logging_config import get_logger

logger = get_logger("flood_cleanup")


def cleanup_expired_flood_reports(db: Session) -> dict:
    """
    Hàm xử lý nghiệp vụ:
    Quét các điểm ngập trong CSDL MySQL thỏa mãn 2 điều kiện:
    1. Đã hết hạn (expires_at <= thời điểm hiện tại).
    2. Chưa có xác thực thêm từ quản trị viên (is_verified == False).

    Quy tắc xử lý:
    - Nếu mức ngập là HIGH (lút bánh xe)   -> Hạ xuống MEDIUM, gia hạn thêm 30 phút.
    - Nếu mức ngập là MEDIUM (nửa bánh xe) -> Hạ xuống LOW, gia hạn thêm 30 phút.
    - Nếu mức ngập là LOW (mắt cá chân)    -> Đã hết hạn -> Xóa điểm ngập khỏi CSDL.
    """
    now = datetime.now()
    downgraded_count = 0
    deleted_count = 0

    try:
        # Truy vấn các điểm ngập đã hết hạn và chưa được xác thực
        expired_reports = (
            db.query(FloodReport)
            .filter(
                FloodReport.expires_at.is_not(None),
                FloodReport.expires_at <= now,
                FloodReport.is_verified == False,
            )
            .all()
        )

        for report in expired_reports:
            # 1. Mức ngập nặng (high) -> Hạ cấp xuống mức vừa (medium)
            if report.severity_level == SeverityLevel.HIGH:
                report.severity_level = SeverityLevel.MEDIUM
                report.expires_at = now + timedelta(minutes=30)
                downgraded_count += 1
                logger.info("Điểm ngập #%d: Hạ cấp từ HIGH xuống MEDIUM (Gia hạn thêm 30 phút)", report.id)

            # 2. Mức ngập vừa (medium) -> Hạ cấp xuống mức nhẹ (low)
            elif report.severity_level == SeverityLevel.MEDIUM:
                report.severity_level = SeverityLevel.LOW
                report.expires_at = now + timedelta(minutes=30)
                downgraded_count += 1
                logger.info("Điểm ngập #%d: Hạ cấp từ MEDIUM xuống LOW (Gia hạn thêm 30 phút)", report.id)

            # 3. Mức ngập nhẹ (low) đã hết hạn -> Nước đã rút, xóa điểm ngập
            else:
                report_id = report.id
                db.delete(report)
                deleted_count += 1
                logger.info("Điểm ngập #%d: Đã xóa khỏi CSDL do hết hạn ngập", report_id)

        # Lưu toàn bộ thay đổi vào CSDL
        if downgraded_count > 0 or deleted_count > 0:
            db.commit()
            logger.info(
                "Đã hoàn thành dọn dẹp: Hạ cấp %d điểm, Xóa %d điểm ngập.",
                downgraded_count,
                deleted_count,
            )

        return {
            "status": "success",
            "downgraded_count": downgraded_count,
            "deleted_count": deleted_count,
            "checked_at": now.isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.exception("Lỗi khi thực hiện task hạ cấp/xóa điểm ngập: %s", e)
        return {
            "status": "error",
            "message": str(e),
            "downgraded_count": downgraded_count,
            "deleted_count": deleted_count,
        }


async def start_flood_cleanup_background_task(interval_seconds: int = 60):
    """
    Task chạy ngầm định kỳ bằng asyncio (Background Task):
    Cứ mỗi `interval_seconds` giây (mặc định 60 giây), task sẽ tự động thức dậy,
    mở session kết nối MySQL, kiểm tra và dọn dẹp các điểm ngập hết hạn.
    """
    logger.info("Bắt đầu Background Task tự động dọn dẹp điểm ngập (Chu kỳ: %d giây/lần)", interval_seconds)

    while True:
        try:
            await asyncio.sleep(interval_seconds)

            # Mở Database Session riêng cho tác vụ chạy ngầm
            db = SessionLocal()
            try:
                cleanup_expired_flood_reports(db)
            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("Background Task dọn dẹp điểm ngập đã được yêu cầu dừng.")
            break
        except Exception as e:
            logger.error("Lỗi trong quá trình chạy ngầm dọn dẹp điểm ngập: %s", e)
