"""
API Quản trị viên (Admin) quản lý và duyệt các điểm ngập lụt
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.flood import FloodReportCreate, FloodReportUpdate, FloodReportResponse
from ..services.flood_service import FloodService

router = APIRouter(prefix="/api/v1/admin/floods", tags=["Admin"])

@router.get("", response_model=List[FloodReportResponse], summary="Admin: Xem toàn bộ các điểm ngập")
def admin_list_floods(limit: int = 100, db: Session = Depends(get_db)):
    return FloodService.get_all_floods(db, limit=limit)

@router.post("", response_model=FloodReportResponse, status_code=status.HTTP_201_CREATED, summary="Admin: Thêm điểm ngập thủ công")
def admin_create_flood(report_in: FloodReportCreate, db: Session = Depends(get_db)):
    report = FloodService.create_report(db, report_in, client_ip="admin")
    # Tự động xác thực điểm ngập do admin tạo
    FloodService.verify_report(db, report.id)
    return report

@router.put("/{flood_id}", response_model=FloodReportResponse, summary="Admin: Cập nhật thông tin điểm ngập")
def admin_update_flood(flood_id: int, update_in: FloodReportUpdate, db: Session = Depends(get_db)):
    updated = FloodService.update_report(db, flood_id, update_in)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy điểm ngập có ID {flood_id}")
    return updated

@router.delete("/{flood_id}", summary="Admin: Xóa điểm ngập")
def admin_delete_flood(flood_id: int, db: Session = Depends(get_db)):
    success = FloodService.delete_report(db, flood_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy điểm ngập có ID {flood_id}")
    return {"message": f"Đã xóa thành công điểm ngập #{flood_id}", "success": True}

@router.patch("/{flood_id}/verify", response_model=FloodReportResponse, summary="Admin: Duyệt báo cáo điểm ngập (is_verified = True)")
def admin_verify_flood(flood_id: int, db: Session = Depends(get_db)):
    verified = FloodService.verify_report(db, flood_id)
    if not verified:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy điểm ngập có ID {flood_id}")
    return verified
