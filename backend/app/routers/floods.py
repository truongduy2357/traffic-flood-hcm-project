"""
API Điểm ngập lụt dành cho Người dùng & Báo cáo cộng đồng (Crowdsourcing).
Hỗ trợ dữ liệu không gian POINT SRID 4326 và Rate Limiting chống spam (SRS FR3).
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request, status, Query
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.flood_report import FloodReportCreate, FloodReportResponse
from ..services.flood_service import FloodService

router = APIRouter(prefix="/api/v1/floods", tags=["Floods"])


@router.get(
    "",
    response_model=List[FloodReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách các điểm đang ngập tại TP.HCM",
    response_description="Danh sách các điểm ngập còn hiệu lực kèm tọa độ không gian GPS [lat, lng]",
    responses={
        200: {
            "description": "Truy vấn danh sách điểm ngập thành công",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "title": "Đường Nguyễn Hữu Cảnh, Bình Thạnh",
                            "description": "Ngập sâu đoạn chân cầu vượt Thủ Thiêm",
                            "latitude": 10.7932,
                            "longitude": 106.7214,
                            "severity_level": "high",
                            "water_depth_cm": 45,
                            "radius_meters": 80,
                            "is_verified": True,
                            "reported_at": "2026-11-23T08:00:00",
                            "expires_at": "2026-11-24T08:00:00",
                            "coordinates": [10.7932, 106.7214]
                        }
                    ]
                }
            }
        },
        500: {"description": "Lỗi máy chủ nội bộ hoặc lỗi kết nối cơ sở dữ liệu MySQL"}
    }
)
def list_active_floods(db: Session = Depends(get_db)):
    """
    Truy vấn danh sách tất cả các điểm ngập đang hoạt động tại TP. Hồ Chí Minh:
    - **Điều kiện lọc:** `expires_at IS NULL` hoặc `expires_at > NOW()` (chưa hết hạn).
    - **Dữ liệu không gian:** Tọa độ lưu trong MySQL dạng `POINT SRID 4326` được tự động chuyển đổi thành mảng `[latitude, longitude]`.
    - **Sắp xếp:** Các báo cáo mới nhất được ưu tiên xếp lên đầu.
    """
    floods = FloodService.get_active_floods(db)
    return floods


@router.post(
    "",
    response_model=FloodReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Người dân gửi báo cáo điểm ngập mới (Crowdsourcing)",
    response_description="Báo cáo điểm ngập đã được tiếp nhận và lưu vào CSDL với chuẩn SRID 4326",
    responses={
        201: {
            "description": "Báo cáo điểm ngập được tạo thành công",
            "content": {
                "application/json": {
                    "example": {
                        "id": 12,
                        "title": "Chân cầu vượt Hàng Xanh",
                        "description": "Nước ngập nửa bánh xe, di chuyển khó khăn",
                        "latitude": 10.8015,
                        "longitude": 106.7112,
                        "severity_level": "medium",
                        "water_depth_cm": 30,
                        "radius_meters": 50,
                        "is_verified": False,
                        "reported_at": "2026-11-23T08:30:00",
                        "expires_at": "2026-11-24T08:30:00",
                        "coordinates": [10.8015, 106.7112]
                    }
                }
            }
        },
        400: {"description": "Dữ liệu gửi lên không hợp lệ hoặc thiếu thông tin bắt buộc"},
        422: {"description": "Tọa độ GPS nằm ngoài phạm vi giới hạn TP.HCM (Vĩ độ: 10.37-11.16, Kinh độ: 106.35-106.93)"},
        429: {"description": "Quá giới hạn tần suất gửi báo cáo (Rate Limit chống spam)"},
        500: {"description": "Lỗi hệ thống khi ghi dữ liệu không gian vào MySQL"}
    }
)
def report_flood(
    report_in: FloodReportCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Tiếp nhận thông tin báo cáo điểm ngập lụt từ cộng đồng (FR3.2):
    - **Chống spam:** Áp dụng Rate Limiting theo địa chỉ IP của người gửi.
    - **Kiểm tra địa lý (Restrict Bounds):** Bắt buộc tọa độ GPS phải nằm trong ranh giới TP.HCM (Vĩ độ: `10.37 - 11.16`, Kinh độ: `106.35 - 106.93`).
    - **Lưu trữ CSDL:** Chuyển đổi tọa độ thành đối tượng hình học `POINT(lat lng) SRID 4326` trên MySQL 8.0+.
    - **Trạng thái ban đầu:** `is_verified = False` (chờ Quản trị viên duyệt qua MySQL Workbench hoặc Admin API).
    - **Thời gian hết hạn:** Tự động thiết lập `expires_at = NOW() + 24 giờ`.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    created_flood = FloodService.create_report(db, report_in, client_ip=client_ip)
    return created_flood


@router.post(
    "/cleanup",
    status_code=status.HTTP_200_OK,
    summary="Kích hoạt tác vụ dọn dẹp / hạ cấp điểm ngập hết hạn",
    response_description="Kết quả thống kê số lượng điểm ngập đã được hạ cấp hoặc xóa bỏ",
    responses={
        200: {
            "description": "Tác vụ dọn dẹp thực thi thành công",
            "content": {
                "application/json": {
                    "example": {
                        "downgraded_count": 2,
                        "deleted_count": 1,
                        "message": "Đã xử lý xong các điểm ngập quá hạn."
                    }
                }
            }
        }
    }
)
def trigger_flood_cleanup(db: Session = Depends(get_db)):
    """
    Kích hoạt tiến trình dọn dẹp điểm ngập (SRS FR3.3):
    - Tự động **hạ cấp độ ngập** (`high` -> `medium` -> `low`) đối với các điểm đã quá hạn `expires_at` mà không có báo cáo mới.
    - Tự động **xóa hoàn toàn** các điểm ngập cấp `low` đã hết hạn.
    """
    from app.core.flood_cleanup import cleanup_expired_flood_reports
    return cleanup_expired_flood_reports(db)
