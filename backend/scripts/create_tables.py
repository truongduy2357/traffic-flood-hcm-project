import sys
import argparse
from pathlib import Path

# Đảm bảo import được app dù chạy từ root hay từ thư mục backend
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.dialects import mysql

from app.core.config import settings
from app.db.session import engine, Base
from app.models.flood_report import FloodReport, SeverityLevel
from app.models.spatial import Point


def get_compiled_ddl() -> str:
    """Sinh toàn bộ câu lệnh SQL DDL (Table + Spatial Index) cho MySQL dialect."""
    table_ddl = str(sa.schema.CreateTable(FloodReport.__table__).compile(dialect=mysql.dialect()))
    index_ddls = []
    for idx in FloodReport.__table__.indexes:
        index_ddl = str(sa.schema.CreateIndex(idx).compile(dialect=mysql.dialect()))
        index_ddls.append(index_ddl)

    full_sql = (
        f"-- ==========================================================\n"
        f"-- AUTO-GENERATED SQL DDL FOR MYSQL 8.0+\n"
        f"-- DATABASE: {settings.DB_NAME}\n"
        f"-- TABLE: flood_reports (POINT SRID 4326 + SPATIAL INDEX)\n"
        f"-- ==========================================================\n\n"
        f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}`\n"
        f"    CHARACTER SET utf8mb4\n"
        f"    COLLATE utf8mb4_unicode_ci;\n\n"
        f"USE `{settings.DB_NAME}`;\n\n"
        f"{table_ddl.strip()};\n\n"
    )
    for idx_sql in index_ddls:
        full_sql += f"{idx_sql.strip()};\n"

    return full_sql


def create_database_if_not_exists() -> bool:
    """Tạo database MySQL nếu chưa có trước khi kết nối vào schema."""
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset="utf8mb4",
        )
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        conn.commit()
        conn.close()
        print(f"[OK] Cơ sở dữ liệu '{settings.DB_NAME}' đã sẵn sàng.")
        return True
    except Exception as e:
        print(f"[CẢNH BÁO] Không thể tự động tạo database qua PyMySQL: {e}")
        return False


def init_and_verify_tables() -> bool:
    """
    Thực hiện tạo bảng flood_reports và đảm bảo cấu hình SPATIAL INDEX trên cột location.
    Xác nhận lại trạng thái của index sau khi tạo.
    """
    print("=" * 70)
    print("BẮT ĐẦU QUÁ TRÌNH TẠO BẢNG & THIẾT LẬP SPATIAL INDEX")
    print(f"Database Target: {settings.DB_NAME} ({settings.DB_HOST}:{settings.DB_PORT})")
    print(f"Table Name:      {FloodReport.__tablename__}")
    print(f"Spatial Column:  location (POINT SRID {settings.SPATIAL_SRID})")
    print("=" * 70)

    # 1. Thử tạo database nếu chưa tồn tại
    create_database_if_not_exists()

    # 2. Tạo bảng thông qua SQLAlchemy metadata
    try:
        print("\n[1/3] Đang kết nối tới MySQL và tạo bảng flood_reports...")
        Base.metadata.create_all(bind=engine)
        print("[OK] Bảng 'flood_reports' đã được tạo thành công.")
    except Exception as e:
        print(f"\n[LỖI] Không thể tạo bảng qua SQLAlchemy Engine:")
        print(f"      Chi tiết: {e}")
        print("\n[HƯỚNG DẪN DỰ PHÒNG]:")
        print(f"  - Đảm bảo MySQL server 8.0+ đang chạy trên cổng {settings.DB_PORT}.")
        print(f"  - Kiểm tra mật khẩu tài khoản '{settings.DB_USER}' trong file .env.")
        print(f"  - Bạn có thể copy mã SQL sinh sẵn bằng lệnh: python {Path(__file__).name} --sql")
        print(f"    hoặc chạy file: backend/migrations/001_create_flood_reports.sql trong MySQL Workbench.")
        return False

    # 3. Đảm bảo SPATIAL INDEX tồn tại trên cột location
    try:
        print("\n[2/3] Kiểm tra và thiết lập SPATIAL INDEX trên cột 'location'...")
        with engine.connect() as conn:
            # Kiểm tra xem index đã tồn tại chưa
            result = conn.execute(
                text(
                    "SHOW INDEX FROM flood_reports WHERE Column_name = 'location';"
                )
            ).fetchall()

            has_spatial_index = False
            for row in result:
                # row[10] là Index_type trong MySQL SHOW INDEX
                # Các cột: Table, Non_unique, Key_name, Seq_in_index, Column_name, Collation, Cardinality, Sub_part, Packed, Null, Index_type
                index_type = getattr(row, "Index_type", None) or (row[10] if len(row) > 10 else "")
                key_name = getattr(row, "Key_name", None) or (row[2] if len(row) > 2 else "")
                if str(index_type).upper() == "SPATIAL":
                    has_spatial_index = True
                    print(f"[OK] Đã phát hiện SPATIAL INDEX: '{key_name}' (Type: {index_type})")
                    break

            if not has_spatial_index:
                print("      Chưa có SPATIAL INDEX, đang thực thi lệnh DDL bổ sung...")
                conn.execute(
                    text(
                        "CREATE SPATIAL INDEX idx_flood_reports_location ON flood_reports (location);"
                    )
                )
                conn.commit()
                print("[OK] Đã tạo thành công 'SPATIAL INDEX idx_flood_reports_location ON flood_reports (location)'.")

    except Exception as e:
        print(f"[CẢNH BÁO] Kiểm tra SPATIAL INDEX qua raw SQL gặp lỗi: {e}")

    # 4. Xác nhận chi tiết cấu trúc bảng và index
    try:
        print("\n[3/3] Xác thực lại cấu trúc không gian của bảng 'flood_reports'...")
        with engine.connect() as conn:
            indexes = conn.execute(
                text("SHOW INDEX FROM flood_reports;")
            ).fetchall()
            print("\nDanh sách Indexes trên bảng flood_reports:")
            for idx in indexes:
                k_name = getattr(idx, "Key_name", None) or idx[2]
                col_name = getattr(idx, "Column_name", None) or idx[4]
                idx_type = getattr(idx, "Index_type", None) or (idx[10] if len(idx) > 10 else "BTREE")
                print(f"  - Key Name: {k_name:<30} | Column: {col_name:<12} | Index Type: {idx_type}")

        print("\n" + "=" * 70)
        print("HOÀN TẤT THÀNH CÔNG: Bảng flood_reports và SPATIAL INDEX đã sẵn sàng!")
        print("=" * 70)
        return True
    except Exception as e:
        print(f"[CẢNH BÁO] Không thể đọc danh sách index: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Script khởi tạo bảng flood_reports và cấu hình bắt buộc SPATIAL INDEX cho MySQL 8.0+"
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="In ra toàn bộ câu lệnh SQL DDL chuẩn MySQL 8.0+ (không cần kết nối database)",
    )
    args = parser.parse_args()

    if args.sql:
        print(get_compiled_ddl())
        return

    success = init_and_verify_tables()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

