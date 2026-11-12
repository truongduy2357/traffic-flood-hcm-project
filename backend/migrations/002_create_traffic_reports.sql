-- ==============================================================================
-- DỰ ÁN: HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
-- MIGRATION SCRIPT: 002_create_traffic_reports.sql
-- MỤC ĐÍCH:
--   1. Tạo bảng traffic_reports lưu trữ điểm kẹt xe với cột location POINT SRID 4326.
--   2. BẮT BUỘC thiết lập SPATIAL INDEX trên cột location.
--   3. Hỗ trợ truy vấn không gian phát hiện kẹt xe trên tuyến đường.
--
-- YÊU CẦU: MySQL 8.0+, Database flood_warning_db đã tồn tại (chạy 001 trước)
-- THAM CHIẾU SRS: Mục 3.2.2 - Hiển thị Tình trạng Giao thông
-- ==============================================================================

USE `flood_warning_db`;

-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  TẠO BẢNG traffic_reports (Báo cáo điểm kẹt xe)                        ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

CREATE TABLE IF NOT EXISTS `traffic_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY
        COMMENT 'Mã định danh báo cáo kẹt xe (PK, Auto Increment)',

    `location` POINT NOT NULL SRID 4326
        COMMENT 'Tọa độ GPS điểm kẹt xe theo chuẩn SRID 4326 (WGS 84): POINT(lat lng)',

    `congestion_level` ENUM('light', 'moderate', 'heavy') NOT NULL DEFAULT 'light'
        COMMENT 'Mức độ kẹt xe: light (nhẹ), moderate (trung bình), heavy (nặng)',

    `description` VARCHAR(500) NULL DEFAULT NULL
        COMMENT 'Mô tả chi tiết tình trạng kẹt xe (tùy chọn)',

    `reported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Thời điểm người dùng gửi báo cáo kẹt xe',

    `is_verified` BOOLEAN NOT NULL DEFAULT FALSE
        COMMENT 'Trạng thái xác minh bởi Quản trị viên (Admin)',

    `expires_at` DATETIME NULL DEFAULT NULL
        COMMENT 'Thời điểm tự động hết hạn báo cáo kẹt xe',

    -- CẤU HÌNH BẮT BUỘC: SPATIAL INDEX cho truy vấn không gian nhanh (R-Tree)
    SPATIAL INDEX `idx_traffic_reports_location` (`location`)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Bảng lưu trữ thông tin các điểm kẹt xe tại TP.HCM — Spatial Index trên location (R-Tree)';

-- Xác nhận
DESCRIBE `traffic_reports`;
SHOW INDEX FROM `traffic_reports` WHERE Key_name = 'idx_traffic_reports_location';

