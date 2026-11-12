-- ==============================================================================
-- DỰ ÁN: HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
-- MIGRATION SCRIPT: 001_create_flood_reports.sql
-- MỤC ĐÍCH:
--   1. Tạo cơ sở dữ liệu MySQL 8.0+ chuẩn utf8mb4 nếu chưa tồn tại.
--   2. Tạo bảng flood_reports với cột location kiểu POINT SRID 4326 (WGS 84).
--   3. BẮT BUỘC thiết lập SPATIAL INDEX trên cột location để tối ưu tốc độ
--      truy vấn không gian (ST_Intersects, ST_Distance_Sphere, ST_Contains).
--
-- YÊU CẦU: MySQL 8.0+ (hỗ trợ SRID trên cột POINT và InnoDB Spatial Index)
-- THAM CHIẾU SRS: Mục 3.4 - Yêu cầu Cơ sở dữ liệu, Task 7, 8, 9
-- ==============================================================================

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  BƯỚC 1: KHỞI TẠO DATABASE                                              ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

CREATE DATABASE IF NOT EXISTS `flood_warning_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `flood_warning_db`;

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  BƯỚC 2: TẠO BẢNG flood_reports                                         ║
-- ║                                                                          ║
-- ║  Lưu ý kỹ thuật cho MySQL 8.0+:                                         ║
-- ║  • Cột location lưu trữ kiểu POINT với SRID 4326 (WGS 84 / GPS).       ║
-- ║  • SRID 4326 đồng bộ chuẩn tọa độ với Google Maps API.                  ║
-- ║  • Cột location BẮT BUỘC là NOT NULL → MySQL mới cho phép SPATIAL INDEX. ║
-- ║  • SPATIAL INDEX xây dựng cấu trúc cây R-Tree → truy vấn <200ms.        ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

CREATE TABLE IF NOT EXISTS `flood_reports` (
    -- Khóa chính tự tăng
    `id` INT AUTO_INCREMENT PRIMARY KEY
        COMMENT 'Mã định danh báo cáo ngập (PK, Auto Increment)',

    -- Tọa độ GPS kiểu POINT SRID 4326 — BẮT BUỘC NOT NULL để tạo SPATIAL INDEX
    `location` POINT NOT NULL SRID 4326
        COMMENT 'Tọa độ GPS điểm ngập theo chuẩn SRID 4326 (WGS 84): POINT(lat lng)',

    -- Mức độ ngập lụt theo 3 cấp (SRS mục 3.2.3)
    `severity_level` ENUM('low', 'medium', 'high') NOT NULL DEFAULT 'low'
        COMMENT 'Mức độ ngập: low (mắt cá chân ≤20cm), medium (nửa bánh xe 20-40cm), high (lút bánh xe >40cm)',

    -- Thời điểm tạo báo cáo
    `reported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Thời điểm người dùng gửi báo cáo ngập',

    -- Trạng thái xác minh bởi Admin
    `is_verified` BOOLEAN NOT NULL DEFAULT FALSE
        COMMENT 'Trạng thái xác minh bởi Quản trị viên (Admin) — TRUE: đã duyệt',

    -- Thời điểm hết hạn tự động (SRS FR3.3: Background Job hạ cấp/xóa)
    `expires_at` DATETIME NULL DEFAULT NULL
        COMMENT 'Thời điểm tự động hạ cấp hoặc hết hạn điểm ngập (NULL = không hết hạn)',

    -- ┌──────────────────────────────────────────────────────────────────────┐
    -- │  CẤU HÌNH BẮT BUỘC: SPATIAL INDEX TRÊN CỘT LOCATION               │
    -- │                                                                      │
    -- │  MySQL sử dụng cấu trúc R-Tree để đánh chỉ mục không gian:         │
    -- │  • Tăng tốc các hàm: ST_Intersects, ST_Contains, ST_Within          │
    -- │  • Tối ưu truy vấn ST_Distance_Sphere (tìm điểm ngập trong bán kính)│
    -- │  • Đảm bảo hiệu năng API phản hồi < 200ms (SRS mục 3.3.1)          │
    -- │                                                                      │
    -- │  Yêu cầu tiên quyết:                                                │
    -- │  1. Cột location phải là NOT NULL                                    │
    -- │  2. Cột location phải khai báo SRID (ở đây là 4326)                 │
    -- │  3. Storage Engine phải là InnoDB (MySQL 8.0+)                       │
    -- └──────────────────────────────────────────────────────────────────────┘
    SPATIAL INDEX `idx_flood_reports_location` (`location`)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Bảng lưu trữ thông tin các điểm ngập lụt tại TP.HCM — Spatial Index trên location (R-Tree)';


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  BƯỚC 3: KIỂM TRA & XÁC NHẬN (VERIFICATION QUERIES)                    ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

-- 3a. Kiểm tra cấu trúc bảng — xác nhận cột location là POINT SRID 4326
DESCRIBE `flood_reports`;

-- 3b. Kiểm tra SPATIAL INDEX đã được thiết lập thành công
--     Kết quả mong đợi: Index_type = 'SPATIAL', Key_name = 'idx_flood_reports_location'
SHOW INDEX FROM `flood_reports` WHERE Key_name = 'idx_flood_reports_location';

-- 3c. Xác nhận chi tiết SRID trên cột location qua INFORMATION_SCHEMA
SELECT COLUMN_NAME, DATA_TYPE, SRS_ID
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'flood_warning_db'
  AND TABLE_NAME   = 'flood_reports'
  AND COLUMN_NAME  = 'location';


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  BƯỚC 4: DỮ LIỆU MẪU & TEST TRUY VẤN KHÔNG GIAN                       ║
-- ║  (Uncomment để chạy thử sau khi tạo bảng thành công)                    ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

-- 4a. Chèn thử 3 điểm ngập mẫu tại TPHCM
-- INSERT INTO `flood_reports` (`location`, `severity_level`, `is_verified`, `expires_at`)
-- VALUES
--     (ST_GeomFromText('POINT(10.772500 106.698000)', 4326), 'high',   TRUE,  DATE_ADD(NOW(), INTERVAL 24 HOUR)),
--     (ST_GeomFromText('POINT(10.762622 106.660172)', 4326), 'medium', FALSE, DATE_ADD(NOW(), INTERVAL 12 HOUR)),
--     (ST_GeomFromText('POINT(10.848820 106.786316)', 4326), 'low',    FALSE, DATE_ADD(NOW(), INTERVAL 6 HOUR));

-- 4b. Đọc lại dữ liệu dưới dạng WKT
-- SELECT id, ST_AsText(location) AS location_wkt, severity_level, reported_at, is_verified
-- FROM `flood_reports`;

-- 4c. Ví dụ: Tìm các điểm ngập trong bán kính 2km từ Nhà thờ Đức Bà (10.779785, 106.699018)
--     Truy vấn này tận dụng SPATIAL INDEX (R-Tree) để quét nhanh
-- SELECT id, severity_level,
--        ST_Distance_Sphere(location, ST_GeomFromText('POINT(10.779785 106.699018)', 4326)) AS distance_meters
-- FROM `flood_reports`
-- WHERE ST_Distance_Sphere(location, ST_GeomFromText('POINT(10.779785 106.699018)', 4326)) <= 2000
-- ORDER BY distance_meters ASC;
