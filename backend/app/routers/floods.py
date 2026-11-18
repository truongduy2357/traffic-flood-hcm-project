"""
API Điểm ngập lụt dành cho Người dùng & Báo cáo cộng đồng (Crowdsourcing)
"""
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.flood_report import FloodReportCreate, FloodReportResponse
from ..services.flood_service import FloodService

router = APIRouter(prefix="/api/v1/floods", tags=["Floods"])

@router.get("", response_model=List[FloodReportResponse], summary="Lấy danh sách các điểm đang ngập tại TPHCM")
def list_active_floods(db: Session = Depends(get_db)):
    """
    Trả về danh sách các điểm ngập còn hiệu lực (expires_at > hiện tại).
    Dữ liệu vị trí được chuyển đổi thành tọa độ chuẩn [latitude, longitude] SRID 4326.
    """
    floods = FloodService.get_active_floods(db)
    return floods

@router.post(
    "",
    response_model=FloodReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Người dân gửi báo cáo điểm ngập lụt mới (Crowdsourcing - Rate Limited)"
)
def report_flood(
    report_in: FloodReportCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Nhận dữ liệu báo cáo điểm ngập từ người dùng.
    - Áp dụng Rate Limiting chống spam request.
    - Validate tọa độ GPS nằm trong giới hạn TPHCM (10.37-11.16, 106.35-106.93).
    - Lưu vào CSDL với chuẩn SRID 4326.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    created_flood = FloodService.create_report(db, report_in, client_ip=client_ip)
    return created_flood
