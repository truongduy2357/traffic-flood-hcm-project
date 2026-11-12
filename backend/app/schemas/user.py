from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field


# 1. Phân quyền người dùng theo đặc tả SRS
class UserRole(str, Enum):
    ADMIN = "admin"          # Quản trị viên: duyệt báo cáo ngập, xem Spatial View, quản lý hệ thống
    MODERATOR = "moderator"  # Kiểm duyệt viên: xác minh thông tin ngập lụt từ cộng đồng
    USER = "user"            # Người dùng phổ thông / Người dân: gửi báo cáo, tìm đường né ngập


# 2. Schema gốc: Các thông tin cơ bản của người dùng
class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Tên đăng nhập (chỉ gồm chữ cái, số, gạch dưới và gạch ngang)",
        examples=["nguyenvana"],
    )
    email: EmailStr = Field(
        ...,
        description="Địa chỉ email hợp lệ để nhận thông báo cảnh báo ngập",
        examples=["nguyenvana@example.com"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=100,
        description="Họ và tên người dùng",
        examples=["Nguyễn Văn A"],
    )
    phone_number: str | None = Field(
        default=None,
        pattern=r"^(0|\+84)[0-9]{9}$",
        description="Số điện thoại liên hệ (định dạng Việt Nam)",
        examples=["0901234567"],
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="Vai trò trong hệ thống",
    )
    is_active: bool = Field(
        default=True,
        description="Trạng thái tài khoản đang hoạt động",
    )


# 3. Schema khi đăng ký / tạo mới tài khoản (POST /api/v1/auth/register hoặc /users)
class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Mật khẩu tài khoản (tối thiểu 6 ký tự)",
        examples=["MatKhauBaoMat123@"],
    )


# 4. Schema khi cập nhật thông tin tài khoản (PUT / PATCH /api/v1/users/{id})
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    phone_number: str | None = None
    password: str | None = Field(
        default=None,
        min_length=6,
        max_length=128,
        description="Mật khẩu mới (nếu muốn đổi)",
    )
    is_active: bool | None = None
    role: UserRole | None = None


# 5. Schema khi trả về cho Client (GET /api/v1/users/me hoặc /users/{id}) - Ẩn mật khẩu
class UserResponse(UserBase):
    id: int = Field(..., description="ID định danh duy nhất của người dùng")
    created_at: datetime = Field(..., description="Thời điểm đăng ký tài khoản")
    updated_at: datetime | None = Field(default=None, description="Thời điểm cập nhật gần nhất")

    class Config:
        from_attributes = True



