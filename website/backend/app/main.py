"""
HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from app.core.config import settings
from app.middleware.cors import setup_cors


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "REST API hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM. "
        "Hỗ trợ truy vấn không gian (Spatial Query) trên MySQL 8.0+ với SRID 4326."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Gắn CORS — toàn bộ logic nằm trong app/middleware/cors.py
setup_cors(app)


@app.on_event("startup")
async def on_startup():
    try:
        from app.db.init_db import init_db
        init_db()
        print(f"[STARTUP] Database '{settings.DB_NAME}' & Spatial Index đã sẵn sàng.")
    except Exception as e:
        print(f"[STARTUP WARNING] Không thể khởi tạo database tự động: {e}")


@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    return {"status": "ok", "app_name": settings.APP_NAME, "environment": settings.APP_ENV}


@app.get("/", tags=["System"], summary="Trang chủ API")
async def root():
    return {"message": settings.APP_NAME, "docs": "/docs", "health": "/health"}
