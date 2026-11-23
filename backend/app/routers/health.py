"""
Endpoint kiểm tra sức khỏe hệ thống và cơ sở dữ liệu MySQL (Task 14).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.session import get_db, DATABASE_ENGINE_NAME, IS_MYSQL

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Kiểm tra trạng thái hoạt động của Backend Server và CSDL MySQL",
    response_description="Trạng thái sống/chết của máy chủ và kết nối CSDL",
    responses={
        200: {
            "description": "Hệ thống hoạt động bình thường (Healthy)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2026-11-23T08:30:00",
                        "database": {
                            "engine": "MySQL 8.0+",
                            "is_mysql": True,
                            "status": "connected"
                        },
                        "service": "Hệ thống Cảnh báo Kẹt xe & Ngập lụt TPHCM"
                    }
                }
            }
        },
        503: {"description": "Dịch vụ gián đoạn hoặc mất kết nối cơ sở dữ liệu"}
    }
)
def health_check(db: Session = Depends(get_db)):
    """
    Kiểm tra tình trạng hoạt động (Health-check API):
    - Kiểm tra phản hồi của web server FastAPI.
    - Thực thi truy vấn `SELECT 1` kiểm tra kết nối CSDL MySQL 8.0+.
    - Trả về thông số thời gian thực và tên engine cơ sở dữ liệu.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    is_healthy = "error" not in db_status
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "engine": DATABASE_ENGINE_NAME,
            "is_mysql": IS_MYSQL,
            "status": db_status
        },
        "service": "Hệ thống Cảnh báo Kẹt xe & Ngập lụt TPHCM"
    }
