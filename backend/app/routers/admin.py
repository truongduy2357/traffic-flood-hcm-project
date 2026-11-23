"""
API Quản trị viên (Admin) quản lý, xác duyệt và thao tác với các điểm ngập lụt.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.flood import FloodReportCreate, FloodReportUpdate, FloodReportResponse
from ..services.flood_service import FloodService

router = APIRouter(prefix="/api/v1/admin/floods", tags=["Admin"])


@router.get(
    "",
    response_model=List[FloodReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin: Xem toàn bộ danh sách điểm ngập (kể cả chưa duyệt và hết hạn)",
    response_description="Danh sách tất cả các bản ghi điểm ngập trong hệ thống phục vụ quản trị",
    responses={
        200: {"description": "Lấy danh sách thành công"},
        500: {"description": "Lỗi kết nối cơ sở dữ liệu"}
    }
)
def admin_list_floods(
    limit: int = Query(default=100, ge=1, le=500, description="Số lượng bản ghi tối đa"),
    db: Session = Depends(get_db)
):
    """
    Dành riêng cho Quản trị viên:
    - Truy vấn toàn bộ các điểm ngập trong cơ sở dữ liệu `flood_reports`.
    - Bao gồm các báo cáo chưa được xác minh (`is_verified = False`) và các điểm đã hết hạn để xem lịch sử.
    """
    return FloodService.get_all_floods(db, limit=limit)


@router.post(
    "",
    response_model=FloodReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Thêm thủ công điểm ngập lụt mới với tọa độ không gian",
    response_description="Bản ghi điểm ngập được tạo mới và tự động gắn cờ đã xác minh (is_verified = True)",
    responses={
        201: {"description": "Điểm ngập được thêm thành công"},
        422: {"description": "Dữ liệu tọa độ không nằm trong ranh giới TP.HCM"},
        500: {"description": "Lỗi ghi dữ liệu vào MySQL"}
    }
)
def admin_create_flood(report_in: FloodReportCreate, db: Session = Depends(get_db)):
    """
    Quản trị viên thêm trực tiếp một điểm ngập đã kiểm chứng vào hệ thống:
    - Lưu vị trí dưới dạng `POINT(lat lng) SRID 4326`.
    - Tự động đánh dấu `is_verified = True`.
    """
    report = FloodService.create_report(db, report_in, client_ip="admin")
    FloodService.verify_report(db, report.id)
    return report


@router.put(
    "/{flood_id}",
    response_model=FloodReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Cập nhật thông tin điểm ngập (mức ngập, tọa độ, hạn dùng)",
    response_description="Thông tin điểm ngập sau khi được cập nhật thành công",
    responses={
        200: {"description": "Cập nhật thành công"},
        404: {"description": "Không tìm thấy điểm ngập với ID yêu cầu"},
        422: {"description": "Tọa độ cập nhật mới không hợp lệ"}
    }
)
def admin_update_flood(
    flood_id: int = Path(..., description="ID của điểm ngập cần chỉnh sửa"),
    update_in: FloodReportUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Cho phép Quản trị viên điều chỉnh:
    - Mức độ ngập lụt (`low`, `medium`, `high`).
    - Tọa độ GPS nếu có sai lệch.
    - Gia hạn hoặc rút ngắn thời gian hiệu lực (`expires_at`).
    """
    updated = FloodService.update_report(db, flood_id, update_in)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy điểm ngập có ID {flood_id}")
    return updated


@router.patch(
    "/{flood_id}/verify",
    response_model=FloodReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: Duyệt báo cáo điểm ngập (chuyển is_verified thành True)",
    response_description="Bản ghi điểm ngập sau khi đã được phê duyệt",
    responses={
        200: {"description": "Phê duyệt điểm ngập thành công"},
        404: {"description": "Không tìm thấy điểm ngập với ID yêu cầu"}
    }
)
def admin_verify_flood(
    flood_id: int = Path(..., description="ID của điểm ngập cần duyệt"),
    db: Session = Depends(get_db)
):
    """
    Phê duyệt báo cáo ngập lụt do người dân gửi lên (Crowdsourcing):
    - Đổi trạng thái `is_verified` từ `False` sang `True`.
    - Điểm ngập sau khi duyệt sẽ xuất hiện trong Spatial View `v_flood_verified_spatial` và hiển thị huy hiệu xác minh trên bản đồ.
    """
    verified = FloodService.verify_report(db, flood_id)
    if not verified:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy điểm ngập có ID {flood_id}")
    return verified


@router.delete(
    "/{flood_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin: Xóa điểm ngập khỏi hệ thống",
    response_description="Thông báo xóa thành công",
    responses={
        200: {"description": "Đã xóa điểm ngập thành công"},
        404: {"description": "Không tìm thấy điểm ngập với ID yêu cầu"}
    }
)
def admin_delete_flood(
    flood_id: int = Path(..., description="ID của điểm ngập cần xóa"),
    db: Session = Depends(get_db)
):
    """
    Xóa vĩnh viễn một bản ghi điểm ngập (ví dụ khi nước đã rút hoàn toàn hoặc báo cáo rác/sai sự thật).
    """
    success = FloodService.delete_report(db, flood_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy điểm ngập có ID {flood_id}")
    return {"message": f"Đã xóa thành công điểm ngập #{flood_id}", "success": True}
