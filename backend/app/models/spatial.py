import re
from typing import Optional, Tuple, Union
from sqlalchemy.types import UserDefinedType
from sqlalchemy import func

class Point(UserDefinedType):
    """
    Kiểu dữ liệu không gian POINT trong MySQL 8.0+ hỗ trợ hệ tọa độ SRID.
    
    Đặc tả kỹ thuật:
    - Mặc định SRID = 4326: Chuẩn hệ tọa độ GPS quốc tế (WGS 84).
    - Cú pháp DDL sinh ra trên MySQL: POINT SRID 4326
    - bind_expression: Tự động bọc giá trị bind param trong ST_GeomFromText(:val, 4326).
    - column_expression: Tự động bọc cột trong ST_AsText(col) để trả về chuỗi WKT 'POINT(lat lng)'.
    """
    cache_ok = True

    def __init__(self, srid: int = 4326):
        """Khởi tạo kiểu POINT với SRID (mặc định 4326 cho chuẩn GPS WGS 84)."""
        self.srid = srid

    def get_col_spec(self, **kw) -> str:
        """Sinh đặc tả cột SQL cho MySQL 8.0+: POINT SRID 4326."""
        return f"POINT SRID {self.srid}"

    def bind_expression(self, bindvalue):
        """
        Tự động chuyển đổi chuỗi WKT như 'POINT(10.776889 106.700806)'
        thành đối tượng Geometry của MySQL thông qua hàm ST_GeomFromText.
        """
        return func.ST_GeomFromText(bindvalue, self.srid)

    def column_expression(self, col):
        """
        Tự động chuyển đổi dữ liệu không gian nhị phân (WKB) trong MySQL
        thành chuỗi WKT đọc được 'POINT(lat lng)' thông qua hàm ST_AsText.
        """
        return func.ST_AsText(col)


def create_point_wkt(lat: float, lng: float) -> str:
    """
    Tạo chuỗi WKT 'POINT(lat lng)' từ tọa độ latitude và longitude.
    Theo chuẩn lưu trữ SRID 4326 của hệ thống: Vĩ độ (lat) trước, Kinh độ (lng) sau.
    """
    return f"POINT({lat:.6f} {lng:.6f})"


def parse_point_wkt(wkt_str: Optional[Union[str, bytes]]) -> Tuple[Optional[float], Optional[float]]:
    """
    Phân tích chuỗi WKT 'POINT(lat lng)' thành tuple (latitude, longitude).
    Trả về (None, None) nếu chuỗi không hợp lệ.
    """
    if not wkt_str:
        return None, None

    if isinstance(wkt_str, bytes):
        try:
            wkt_str = wkt_str.decode("utf-8")
        except Exception:
            return None, None

    match = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", str(wkt_str), re.IGNORECASE)
    if match:
        try:
            lat = float(match.group(1))
            lng = float(match.group(2))
            return lat, lng
        except ValueError:
            pass

    return None, None

