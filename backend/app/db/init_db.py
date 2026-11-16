"""
Database initialization module.
Cung cấp hàm init_db() để tự động tạo bảng và đảm bảo SPATIAL INDEX khi khởi động hoặc chạy script.
"""

from app.db.session import engine, Base
from app.models.flood_report import FloodReport
from sqlalchemy import text


def init_db() -> None:
    """Tạo tất cả các bảng và đảm bảo SPATIAL INDEX trên cột location."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        result = conn.execute(
            text("SHOW INDEX FROM flood_reports WHERE Column_name = 'location';")
        ).fetchall()
        has_spatial = any(
            str(getattr(r, "Index_type", r[10] if len(r) > 10 else "")).upper() == "SPATIAL"
            for r in result
        )
        if not has_spatial:
            conn.execute(
                text("CREATE SPATIAL INDEX idx_flood_reports_location ON flood_reports (location);")
            )
            conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database tables & Spatial Index initialized.")

