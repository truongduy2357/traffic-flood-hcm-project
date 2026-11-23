"""
Script khởi tạo dữ liệu mẫu các điểm ngập lụt tại TP.HCM vào CSDL MySQL.
Bao gồm 3 điểm ngập đại diện cho 3 cấp độ: high, medium, low.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app.db.session import engine


SAMPLE_FLOODS = [
    {
        "title": "Đường Nguyễn Hữu Cảnh, Bình Thạnh",
        "description": "Ngập sâu đoạn chân cầu Thủ Thiêm, xe chết máy hàng loạt",
        "latitude": 10.7932,
        "longitude": 106.7214,
        "severity_level": "high",
        "water_depth_cm": 45,
        "radius_meters": 80,
        "is_verified": 1,
        "days_valid": 7,
    },
    {
        "title": "Đường Huỳnh Tấn Phát, Quận 7",
        "description": "Triều cường dâng cao ngập nửa bánh xe",
        "latitude": 10.7428,
        "longitude": 106.7325,
        "severity_level": "medium",
        "water_depth_cm": 30,
        "radius_meters": 60,
        "is_verified": 1,
        "days_valid": 7,
    },
    {
        "title": "Đường Quốc Hương, Thảo Điền",
        "description": "Nước ngập mắt cá chân, các phương tiện di chuyển chậm",
        "latitude": 10.8045,
        "longitude": 106.7321,
        "severity_level": "low",
        "water_depth_cm": 15,
        "radius_meters": 40,
        "is_verified": 0,
        "days_valid": 7,
    },
]


def seed_floods():
    print("Đang kết nối tới MySQL và kiểm tra bảng flood_reports...")
    with engine.begin() as conn:
        # Kiểm tra số lượng bản ghi hiện có
        count = conn.execute(text("SELECT COUNT(*) FROM flood_reports;")).scalar()
        print(f"Số lượng bản ghi hiện có: {count}")

        insert_sql = text("""
            INSERT INTO flood_reports (
                title, description, location, severity_level,
                water_depth_cm, radius_meters, reported_at, is_verified, expires_at
            ) VALUES (
                :title, :description, ST_GeomFromText(:wkt, 4326), :severity_level,
                :water_depth_cm, :radius_meters, NOW(), :is_verified, DATE_ADD(NOW(), INTERVAL :days DAY)
            );
        """)

        added_count = 0
        for item in SAMPLE_FLOODS:
            wkt = f"POINT({item['latitude']:.6f} {item['longitude']:.6f})"
            conn.execute(
                insert_sql,
                {
                    "title": item["title"],
                    "description": item["description"],
                    "wkt": wkt,
                    "severity_level": item["severity_level"],
                    "water_depth_cm": item["water_depth_cm"],
                    "radius_meters": item["radius_meters"],
                    "is_verified": item["is_verified"],
                    "days": item["days_valid"],
                },
            )
            added_count += 1
            print(f"-> Đã thêm: {item['title']} [{item['severity_level'].upper()}] ({item['latitude']}, {item['longitude']})")

        total = conn.execute(text("SELECT COUNT(*) FROM flood_reports;")).scalar()
        print(f"\nThành công! Đã chèn {added_count} điểm ngập mẫu vào CSDL. Tổng số điểm hiện tại: {total}")


if __name__ == "__main__":
    seed_floods()
