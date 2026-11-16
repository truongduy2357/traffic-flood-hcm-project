from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Khởi tạo engine kết nối MySQL 8.0+ qua PyMySQL
# pool_pre_ping=True giúp tự động kiểm tra và phục hồi kết nối bị timeout/drop
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

# Quản lý Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho toàn bộ SQLAlchemy models
Base = declarative_base()

def get_db():
    """FastAPI Dependency cung cấp database session và tự động đóng sau khi hoàn tất request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

