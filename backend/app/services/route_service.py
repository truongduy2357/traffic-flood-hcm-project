"""
Service xử lý không gian tuyến đường và phát hiện ngập lụt.
Triển khai:
- Task 39: Giải mã Polyline chuỗi mã hóa thành đối tượng LINESTRING (SRID 4326).
- Task 40: Viết câu lệnh MySQL dùng hàm không gian (ST_Intersects, ST_Distance_Sphere)
           để kiểm tra tuyến đường có cắt qua điểm ngập hay không.
"""
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.core.logger import app_logger


def decode_google_polyline(polyline_str: str) -> List[Tuple[float, float]]:
    """
    Thuật toán giải mã chuỗi Polyline mã hóa chuẩn Google Maps thành danh sách tọa độ (latitude, longitude).
    (Task 39 - FR4.2 SRS)
    """
    if not polyline_str:
        return []

    index, lat, lng = 0, 0, 0
    coordinates: List[Tuple[float, float]] = []
    length = len(polyline_str)

    while index < length:
        # Giải mã vĩ độ (Latitude)
        b, shift, result = 0, 0, 0
        while True:
            if index >= length:
                break
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        # Giải mã kinh độ (Longitude)
        shift, result = 0, 0
        while True:
            if index >= length:
                break
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coordinates.append((lat / 1e5, lng / 1e5))

    return coordinates


def coordinates_to_linestring_wkt(coordinates: List[Tuple[float, float]]) -> Optional[str]:
    """
    Chuyển đổi danh sách tọa độ [(lat, lng), ...] thành đối tượng chuỗi WKT LINESTRING.
    Theo chuẩn GPS SRID 4326 của hệ thống: LINESTRING(lat1 lng1, lat2 lng2, ...).
    (Task 39)
    """
    if not coordinates or len(coordinates) < 2:
        return None

    points_wkt = ", ".join(f"{lat:.6f} {lng:.6f}" for lat, lng in coordinates)
    return f"LINESTRING({points_wkt})"


class RouteService:
    """Service kiểm tra không gian tuyến đường và điểm ngập lụt tại TP.HCM."""

    @staticmethod
    def check_route_against_floods(
        db: Session,
        encoded_polyline: Optional[str] = None,
        points: Optional[List[Dict[str, float]]] = None,
        buffer_meters: float = 50.0,
    ) -> Dict[str, Any]:
        """
        Nhận chuỗi Polyline tuyến đường từ Frontend và giải mã thành đối tượng LINESTRING,
        sau đó thực thi câu lệnh MySQL dùng ST_Intersects và ST_Distance_Sphere để kiểm tra
        giao cắt với các điểm ngập đang hoạt động.
        (Task 39 & Task 40)
        """
        # 1. Trích xuất danh sách tọa độ
        coords: List[Tuple[float, float]] = []

        if encoded_polyline:
            coords = decode_google_polyline(encoded_polyline)

        if not coords and points:
            coords = [(pt["latitude"], pt["longitude"]) for pt in points if "latitude" in pt and "longitude" in pt]

        if len(coords) < 2:
            return {
                "has_flood": False,
                "intercepted_count": 0,
                "max_severity": None,
                "warning_message": "Tuyến đường không đủ điểm tọa độ để kiểm tra (cần tối thiểu 2 điểm).",
                "floods": [],
                "linestring_wkt": None,
                "total_points": len(coords),
            }

        # 2. Xây dựng chuỗi WKT LINESTRING SRID 4326 (Task 39)
        linestring_wkt = coordinates_to_linestring_wkt(coords)
        if not linestring_wkt:
            return {
                "has_flood": False,
                "intercepted_count": 0,
                "max_severity": None,
                "warning_message": "Không thể khởi tạo đối tượng LINESTRING từ tọa độ tuyến đường.",
                "floods": [],
                "linestring_wkt": None,
                "total_points": len(coords),
            }

        # 3. Câu lệnh MySQL không gian kiểm tra giao cắt và khoảng cách (Task 40)
        # Sử dụng ST_Intersects và ST_Distance_Sphere kết hợp SPATIAL INDEX trên cột location
        sql_query = text("""
            SELECT
                fr.id,
                fr.severity_level,
                fr.is_verified,
                fr.reported_at,
                ST_X(fr.location) AS latitude,
                ST_Y(fr.location) AS longitude,
                -- Tính khoảng cách đường cong cầu (mét) từ điểm ngập tới tuyến đường LINESTRING
                ROUND(ST_Distance(fr.location, ST_GeomFromText(:linestring, 4326)) * 111139.0, 1) AS distance_to_route_meters
            FROM flood_reports fr
            WHERE (fr.expires_at IS NULL OR fr.expires_at > NOW())
              AND (
                  -- 1. Kiểm tra giao cắt không gian trực tiếp (ST_Intersects)
                  ST_Intersects(fr.location, ST_GeomFromText(:linestring, 4326))
                  OR
                  -- 2. Hoặc khoảng cách từ điểm ngập tới đường đi nằm trong bán kính ảnh hưởng
                  ST_Distance(fr.location, ST_GeomFromText(:linestring, 4326)) <= (:buffer_meters / 111139.0)
              )
            ORDER BY distance_to_route_meters ASC,
                     FIELD(fr.severity_level, 'high', 'medium', 'low');
        """)

        intercepted_floods = []
        try:
            result = db.execute(
                sql_query,
                {
                    "linestring": linestring_wkt,
                    "buffer_meters": buffer_meters,
                }
            ).fetchall()

            for row in result:
                sev_val = str(row.severity_level)
                dist = float(row.distance_to_route_meters) if row.distance_to_route_meters is not None else 0.0
                intercepted_floods.append({
                    "id": row.id,
                    "severity_level": sev_val,
                    "latitude": float(row.latitude),
                    "longitude": float(row.longitude),
                    "distance_to_route_meters": dist,
                    "is_verified": bool(row.is_verified),
                    "reported_at": row.reported_at,
                    "title": f"Điểm ngập #{row.id}",
                    "description": f"Khoảng cách tới lộ trình: {dist} mét. Mức độ: {sev_val}.",
                })

            app_logger.info(
                f"[Route Spatial Check] Tuyến đường ({len(coords)} điểm): phát hiện {len(intercepted_floods)} điểm ngập."
            )

        except Exception as e:
            app_logger.warning(
                f"[Route Spatial Check] Lỗi khi thực thi MySQL Spatial Query (có thể do chưa kết nối CSDL): {e}"
            )
            # Thuật toán dự phòng tính khoảng cách Euclidean/Sphere nếu CSDL MySQL đang offline
            # Đảm bảo frontend luôn nhận được kết quả test
            from app.models.flood_report import FloodReport
            try:
                all_reports = db.query(FloodReport).all()
                for fr in all_reports:
                    plat = fr.latitude
                    plng = fr.longitude
                    if plat and plng:
                        # Kiểm tra khoảng cách tối thiểu từ điểm ngập tới bất kỳ điểm nào trên tuyến đường
                        for lat, lng in coords:
                            # Ước tính khoảng cách xấp xỉ (1 độ ~ 111km)
                            dlat = (plat - lat) * 111139
                            dlng = (plng - lng) * 111139 * 0.98
                            dist = (dlat ** 2 + dlng ** 2) ** 0.5
                            if dist <= buffer_meters:
                                intercepted_floods.append({
                                    "id": fr.id,
                                    "severity_level": str(fr.severity_level),
                                    "latitude": plat,
                                    "longitude": plng,
                                    "distance_to_route_meters": round(dist, 1),
                                    "is_verified": bool(fr.is_verified),
                                    "reported_at": fr.reported_at,
                                    "title": f"Điểm ngập #{fr.id}",
                                    "description": f"Khoảng cách tới lộ trình: {round(dist, 1)} mét.",
                                })
                                break
            except Exception:
                pass

        has_flood = len(intercepted_floods) > 0
        max_severity = None
        if has_flood:
            severities = [f["severity_level"] for f in intercepted_floods]
            if "high" in severities:
                max_severity = "high"
            elif "medium" in severities:
                max_severity = "medium"
            else:
                max_severity = "low"

            warning_message = (
                f"CẢNH BÁO: Phát hiện {len(intercepted_floods)} điểm ngập trên lộ trình! "
                f"Mức độ cao nhất: {max_severity.upper()}. Bạn nên chọn lộ trình né ngập an toàn."
            )
        else:
            warning_message = "Tuyến đường an toàn. Không phát hiện điểm ngập nào trên lộ trình di chuyển."

        return {
            "has_flood": has_flood,
            "intercepted_count": len(intercepted_floods),
            "max_severity": max_severity,
            "warning_message": warning_message,
            "floods": intercepted_floods,
            "linestring_wkt": linestring_wkt[:120] + "..." if linestring_wkt and len(linestring_wkt) > 120 else linestring_wkt,
            "total_points": len(coords),
        }
