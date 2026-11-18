
import re
from typing import Optional, Tuple, Union

from sqlalchemy import func
from sqlalchemy.types import UserDefinedType


class Point(UserDefinedType):
    """
    Kiểu dữ liệu POINT trong MySQL 8.0+ với SRID 4326.
    """

    cache_ok = True

    def __init__(self, srid: int = 4326):
        self.srid = srid

    def get_col_spec(self, **kw) -> str:
        return f"POINT SRID {self.srid}"

    def bind_expression(self, bindvalue):
        """Chuyển WKT thành Geometry khi ghi vào MySQL."""
        return func.ST_GeomFromText(bindvalue, self.srid)

    def column_expression(self, col):
        """Chuyển Geometry thành WKT khi đọc từ MySQL."""
        return func.ST_AsText(col)


def create_point_wkt(lat: float, lng: float) -> str:
    """
    Tạo WKT POINT theo thứ tự trục mà project đang sử dụng:
    POINT(latitude longitude).
    """
    return f"POINT({lat:.6f} {lng:.6f})"


def parse_point_wkt(
    wkt_str: Optional[Union[str, bytes]]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Phân tích WKT POINT thành (latitude, longitude).

    Ví dụ:
        POINT(10.776889 106.700806)

    Kết quả:
        (10.776889, 106.700806)

    Trả về (None, None) nếu dữ liệu không hợp lệ.
    """

    if not wkt_str:
        return None, None

    if isinstance(wkt_str, bytes):
        try:
            wkt_str = wkt_str.decode("utf-8")
        except UnicodeDecodeError:
            return None, None

    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

    pattern = (
        rf"\s*POINT\s*\(\s*({number})\s+"
        rf"({number})\s*\)\s*"
    )

    match = re.fullmatch(pattern, str(wkt_str), re.IGNORECASE)

    if not match:
        return None, None

    try:
        lat = float(match.group(1))
        lng = float(match.group(2))

        # Kiểm tra tọa độ GPS hợp lệ
        if not (-90 <= lat <= 90):
            return None, None

        if not (-180 <= lng <= 180):
            return None, None

        return lat, lng

    except (ValueError, TypeError):
        return None, None
