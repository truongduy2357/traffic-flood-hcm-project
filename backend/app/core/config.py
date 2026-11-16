import os
import json
from pathlib import Path
from typing import List, Union

# Tìm đường dẫn file .env (ưu tiên thư mục hiện tại, backend/, hoặc thư mục gốc)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_LOCATIONS = [
    Path.cwd() / ".env",
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
]

def load_env_file(filepath: Path) -> None:
    """Đọc file .env đơn giản đưa vào os.environ nếu chưa có."""
    if not filepath.is_file():
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key not in os.environ:
                os.environ[key] = val

for env_path in ENV_LOCATIONS:
    if env_path.is_file():
        load_env_file(env_path)
        break

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        APP_NAME: str = "Hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM"
        APP_ENV: str = "development"
        DEBUG: bool = True
        HOST: str = "0.0.0.0"
        PORT: int = 8000

        # Database
        DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/flood_warning_db?charset=utf8mb4"
        DB_HOST: str = "localhost"
        DB_PORT: int = 3306
        DB_USER: str = "root"
        DB_PASSWORD: str = "password"
        DB_NAME: str = "flood_warning_db"
        SPATIAL_SRID: int = 4326

        # Security
        SECRET_KEY: str = "e7b9a2c4e1f8d3c5b7a9f0e2d4c6b8a1f3e5d7c9b0a2f4e6d8c0b2a4f6e8d021"
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

        # Google Maps
        GOOGLE_MAPS_API_KEY: str = "AIzaSyYourGoogleMapsApiKeyHere"

        # CORS
        CORS_ORIGINS: Union[List[str], str] = [
            "http://localhost",
            "http://localhost:8000",
            "http://127.0.0.1:5500",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
        ]

        # Rate Limiting & Business
        RATE_LIMIT_PER_MINUTE: int = 60
        FLOOD_EXPIRATION_HOURS: int = 24

        # Bounds TP.HCM
        TPHCM_MIN_LAT: float = 10.37
        TPHCM_MAX_LAT: float = 11.16
        TPHCM_MIN_LNG: float = 106.35
        TPHCM_MAX_LNG: float = 106.93

        model_config = SettingsConfigDict(
            env_file=str(ENV_LOCATIONS[0]) if ENV_LOCATIONS[0].is_file() else ".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

except ImportError:
    # Dự phòng nếu pydantic-settings chưa được cài đặt
    class Settings:
        APP_NAME: str = os.getenv("APP_NAME", "Hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TPHCM")
        APP_ENV: str = os.getenv("APP_ENV", "development")
        DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
        HOST: str = os.getenv("HOST", "0.0.0.0")
        PORT: int = int(os.getenv("PORT", "8000"))

        DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://root:password@localhost:3306/flood_warning_db?charset=utf8mb4"
        )
        DB_HOST: str = os.getenv("DB_HOST", "localhost")
        DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
        DB_USER: str = os.getenv("DB_USER", "root")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
        DB_NAME: str = os.getenv("DB_NAME", "flood_warning_db")
        SPATIAL_SRID: int = int(os.getenv("SPATIAL_SRID", "4326"))

        SECRET_KEY: str = os.getenv("SECRET_KEY", "e7b9a2c4e1f8d3c5b7a9f0e2d4c6b8a1f3e5d7c9b0a2f4e6d8c0b2a4f6e8d021")
        ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

        GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyYourGoogleMapsApiKeyHere")

        _cors = os.getenv("CORS_ORIGINS", '["http://localhost", "http://localhost:8000", "http://127.0.0.1:5500"]')
        try:
            CORS_ORIGINS: List[str] = json.loads(_cors) if isinstance(_cors, str) and _cors.startswith("[") else [_cors]
        except Exception:
            CORS_ORIGINS: List[str] = ["*"]

        RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        FLOOD_EXPIRATION_HOURS: int = int(os.getenv("FLOOD_EXPIRATION_HOURS", "24"))

        TPHCM_MIN_LAT: float = float(os.getenv("TPHCM_MIN_LAT", "10.37"))
        TPHCM_MAX_LAT: float = float(os.getenv("TPHCM_MAX_LAT", "11.16"))
        TPHCM_MIN_LNG: float = float(os.getenv("TPHCM_MIN_LNG", "106.35"))
        TPHCM_MAX_LNG: float = float(os.getenv("TPHCM_MAX_LNG", "106.93"))

settings = Settings()


def is_in_hcm(lat: float, lng: float) -> bool:
    """
    Kiểm tra tọa độ GPS có nằm trong giới hạn viewport TP.HCM hay không:
    - Vĩ độ (Latitude): 10.37 đến 11.16
    - Kinh độ (Longitude): 106.35 đến 106.93
    """
    return (
        settings.TPHCM_MIN_LAT <= lat <= settings.TPHCM_MAX_LAT
        and settings.TPHCM_MIN_LNG <= lng <= settings.TPHCM_MAX_LNG
    )

