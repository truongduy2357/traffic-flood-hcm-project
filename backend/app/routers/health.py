"""
Endpoint kiểm tra sức khỏe hệ thống (Health Check)
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.session import get_db, DATABASE_ENGINE_NAME, IS_MYSQL

router = APIRouter(tags=["Health"])

@router.get("/health", summary="Kiểm tra trạng thái server và cơ sở dữ liệu")
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if "error" not in db_status else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "engine": DATABASE_ENGINE_NAME,
            "is_mysql": IS_MYSQL,
            "status": db_status
        },
        "service": "Hệ thống Cảnh báo Kẹt xe & Ngập lụt TPHCM"
    }
