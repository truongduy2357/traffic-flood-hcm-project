-- ==============================================================================
-- DỰ ÁN: HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
-- MIGRATION / SCRIPT: 004_check_route_spatial_query.sql
-- MỤC ĐÍCH:
--   Triển khai Task 40 (FR4.2 SRS): Viết câu lệnh MySQL dùng hàm không gian
--   (ST_Intersects, ST_Distance_Sphere) kiểm tra lộ trình LINESTRING có cắt qua
--   điểm ngập không.
--
-- KỸ THUẬT:
--   - Tuyến đường được giải mã từ chuỗi Polyline thành đối tượng LINESTRING SRID 4326.
--   - Sử dụng ST_Intersects để phát hiện giao cắt trực tiếp (tuyến đường cắt xuyên qua điểm ngập).
--   - Sử dụng ST_Distance_Sphere để tính khoảng cách đường cong thực tế (mét)
--     giữa điểm ngập và tuyến đường, so sánh với bán kính an toàn (buffer_meters).
--   - Tối ưu hóa tốc độ truy vấn nhờ SPATIAL INDEX trên cột location (cây R-Tree).
-- ==============================================================================

USE `flood_warning_db`;

-- ------------------------------------------------------------------------------
-- CÂU LỆNH 1: Kiểm tra giao cắt và tính khoảng cách từ điểm ngập tới tuyến đường
-- Tuyến đường mẫu: Đi từ Quận 1 sang Bình Thạnh qua chân cầu Thủ Thiêm
-- LINESTRING(10.7725 106.6980, 10.7850 106.7050, 10.7932 106.7214, 10.8015 106.7112)
-- ------------------------------------------------------------------------------

SET @route_linestring = ST_GeomFromText(
    'LINESTRING(10.772500 106.698000, 10.785000 106.705000, 10.793200 106.721400, 10.801500 106.711200)',
    4326
);

-- Bán kính vùng đệm kiểm tra ảnh hưởng (ví dụ 60 mét)
SET @buffer_meters = 60.0;

-- ------------------------------------------------------------------------------
-- CÂU LỆNH TRUY VẤN KHÔNG GIAN CHÍNH (SPATIAL QUERY CHO TASK 40)
-- ------------------------------------------------------------------------------
SELECT
    fr.id AS flood_id,
    fr.severity_level,
    fr.is_verified,
    fr.reported_at,
    ST_X(fr.location) AS latitude,
    ST_Y(fr.location) AS longitude,

    -- 1. Kiểm tra xem tuyến đường có giao cắt trực tiếp với điểm ngập không
    ST_Intersects(fr.location, @route_linestring) AS is_directly_intersected,

    -- 2. Tính khoảng cách chính xác (mét) từ điểm ngập tới tuyến đường trên mặt cầu Trái Đất
    ROUND(ST_Distance_Sphere(fr.location, @route_linestring), 1) AS distance_to_route_meters

FROM flood_reports fr
WHERE (fr.expires_at IS NULL OR fr.expires_at > NOW())
  AND (
      -- Giao cắt trực tiếp (ST_Intersects)
      ST_Intersects(fr.location, @route_linestring)
      OR
      -- Hoặc nằm trong bán kính vùng đệm an toàn (ST_Distance_Sphere)
      ST_Distance_Sphere(fr.location, @route_linestring) <= @buffer_meters
  )
ORDER BY distance_to_route_meters ASC,
         FIELD(fr.severity_level, 'high', 'medium', 'low');
