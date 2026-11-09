-- ==============================================================================
-- DỰ ÁN: HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
-- MIGRATION SCRIPT: 001_create_flood_reports.sql
-- MỤC ĐÍCH:
--   1. Tạo cơ sở dữ liệu MySQL 8.0+ chuẩn utf8mb4 nếu chưa tồn tại.
--   2. Tạo bảng flood_reports với cột location kiểu POINT SRID 4326 (WGS 84).
--   3. BẮT BUỘC thiết lập SPATIAL INDEX trên cột location để tối ưu tốc độ
--      truy vấn không gian (ST_Intersects, ST_Distance_Sphere, ST_Contains).
-- ==============================================================================

-- 1. Khởi tạo Database nếu chưa có
CREATE DATABASE IF NOT EXISTS `flood_warning_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `flood_warning_db`;

-- 2. Tạo bảng flood_reports
-- Lưu ý kỹ thuật cho MySQL 8.0+:
--   - Cột location lưu trữ kiểu POINT với định danh hệ quy chiếu không gian SRID 4326.
--   - Chuẩn SRID 4326 là chuẩn GPS toàn cầu (WGS 84) khớp với Google Maps API.
--   - Cột location BẮT BUỘC PHẢI LÀ 'NOT NULL' thì MySQL mới cho phép đánh SPATIAL INDEX.
--   - SPATIAL INDEX xây dựng cấu trúc cây R-Tree giúp tìm kiếm không gian cực nhanh (< 200ms).
CREATE TABLE IF NOT EXISTS `flood_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã định danh báo cáo ngập (PK)',
    `location` POINT NOT NULL /*!80003 SRID 4326 */ COMMENT 'Tọa độ GPS điểm ngập theo chuẩn SRID 4326: POINT(lat lng)',
    `severity_level` ENUM('low', 'medium', 'high') NOT NULL DEFAULT 'low' COMMENT 'Mức độ ngập: low (mắt cá chân), medium (nửa bánh xe), high (lút bánh xe)',
    `reported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm gửi báo cáo',
    `is_verified` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Trạng thái xác minh bởi quản trị viên (Admin)',
    `expires_at` DATETIME NULL DEFAULT NULL COMMENT 'Thời điểm tự động hạ cấp hoặc hết hạn điểm ngập',
    
    -- CẤU HÌNH BẮT BUỘC: SPATIAL INDEX TRÊN CỘT LOCATION
    SPATIAL INDEX `idx_flood_reports_location` (`location`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bảng lưu trữ thông tin các điểm ngập lụt tại TP.HCM';

-- ==============================================================================
-- 3. CÂU LỆNH KIỂM TRA & XÁC NHẬN (VERIFICATION QUERIES)
-- ==============================================================================

-- Kiểm tra cấu trúc bảng đã có trường POINT SRID 4326
DESCRIBE `flood_reports`;

-- Kiểm tra SPATIAL INDEX đã được thiết lập thành công
SHOW INDEX FROM `flood_reports` WHERE Key_name = 'idx_flood_reports_location';

-- ==============================================================================
-- 4. DỮ LIỆU MẪU & TEST TRUY VẤN KHÔNG GIAN (SAMPLE USAGE & SPATIAL QUERY)
-- ==============================================================================

-- Chèn thử một điểm ngập tại Bến Thành, Quận 1 (Lat: 10.7725, Lng: 106.6980)
-- Lưu ý: Thứ tự truyền vào hàm ST_GeomFromText theo chuẩn SRS là POINT(lat lng) SRID 4326
-- INSERT INTO `flood_reports` (`location`, `severity_level`, `is_verified`, `expires_at`)
-- VALUES (
--     ST_GeomFromText('POINT(10.772500 106.698000)', 4326),
--     'high',
--     TRUE,
--     DATE_ADD(NOW(), INTERVAL 24 HOUR)
-- );

-- Đọc lại tọa độ hiển thị dưới dạng chuỗi Text (WKT)
-- SELECT id, ST_AsText(location) AS location_wkt, severity_level, reported_at, is_verified FROM `flood_reports`;

-- Ví dụ: Tìm các điểm ngập trong bán kính 2km (2000 mét) từ Nhà thờ Đức Bà (10.779785, 106.699018)
-- Sử dụng ST_Distance_Sphere tối ưu nhờ R-Tree Spatial Index
-- SELECT id, severity_level, 
--        ST_Distance_Sphere(location, ST_GeomFromText('POINT(10.779785 106.699018)', 4326)) AS distance_in_meters
-- FROM `flood_reports`
-- WHERE ST_Distance_Sphere(location, ST_GeomFromText('POINT(10.779785 106.699018)', 4326)) <= 2000;

