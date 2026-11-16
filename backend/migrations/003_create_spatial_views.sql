-- ==============================================================================
-- DỰ ÁN: HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE VÀ NGẬP LỤT TPHCM
-- MIGRATION SCRIPT: 003_create_spatial_views.sql
-- MỤC ĐÍCH:
--   Tạo các Spatial View trong MySQL Workbench hỗ trợ trực quan hóa và
--   quản trị dữ liệu bản đồ. Admin có thể click vào tab "Spatial View"
--   trong MySQL Workbench để hiển thị các điểm ngập/kẹt xe trực tiếp trên
--   bản đồ tích hợp sẵn.
--
-- HƯỚNG DẪN SỬ DỤNG SPATIAL VIEW TRONG MYSQL WORKBENCH:
--   1. Mở MySQL Workbench → kết nối tới flood_warning_db
--   2. Chạy file SQL này để tạo các VIEW
--   3. Chạy SELECT * FROM <tên_view>;
--   4. Trên thanh kết quả, chuyển sang tab "Spatial View" (biểu tượng bản đồ)
--   5. Chọn cột geometry (vd: flood_point / traffic_point) để hiển thị
--   6. Các điểm sẽ được vẽ trực tiếp trên bản đồ trong Workbench
--
-- YÊU CẦU: MySQL 8.0+, Database flood_warning_db và các bảng đã tồn tại
-- THAM CHIẾU SRS: Mục 3.4 - Yêu cầu CSDL, Task 11
-- ==============================================================================

USE `flood_warning_db`;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  VIEW 1: v_flood_spatial — Trực quan hóa TẤT CẢ điểm ngập             ║
-- ║                                                                          ║
-- ║  Hiển thị toàn bộ báo cáo ngập trên Spatial View của MySQL Workbench.   ║
-- ║  Cột flood_point giữ nguyên kiểu GEOMETRY để Workbench vẽ được.         ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

DROP VIEW IF EXISTS `v_flood_spatial`;

CREATE VIEW `v_flood_spatial` AS
SELECT
    fr.id                                       AS report_id,
    fr.location                                 AS flood_point,
    ST_X(fr.location)                           AS latitude,
    ST_Y(fr.location)                           AS longitude,
    fr.severity_level,
    fr.reported_at,
    fr.is_verified,
    fr.expires_at,
    -- Nhãn hiển thị trên Spatial View tooltip
    CONCAT(
        'Ngập [', UPPER(fr.severity_level), '] - ',
        CASE fr.severity_level
            WHEN 'low'    THEN 'Mắt cá chân (≤20cm)'
            WHEN 'medium' THEN 'Nửa bánh xe (20-40cm)'
            WHEN 'high'   THEN 'Lút bánh xe (>40cm)'
        END,
        ' | ', DATE_FORMAT(fr.reported_at, '%d/%m/%Y %H:%i'),
        CASE WHEN fr.is_verified = TRUE THEN ' ✓ Đã duyệt' ELSE ' ○ Chờ duyệt' END
    )                                           AS display_label
FROM `flood_reports` fr
ORDER BY fr.reported_at DESC;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  VIEW 2: v_flood_active_spatial — Chỉ điểm ngập ĐANG CÒN HIỆU LỰC    ║
-- ║                                                                          ║
-- ║  Lọc bỏ các điểm ngập đã hết hạn (expires_at < NOW()).                  ║
-- ║  Admin dùng view này để xem tình trạng ngập thời gian thực.             ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

DROP VIEW IF EXISTS `v_flood_active_spatial`;

CREATE VIEW `v_flood_active_spatial` AS
SELECT
    fr.id                                       AS report_id,
    fr.location                                 AS flood_point,
    ST_X(fr.location)                           AS latitude,
    ST_Y(fr.location)                           AS longitude,
    fr.severity_level,
    fr.reported_at,
    fr.is_verified,
    fr.expires_at,
    -- Tính thời gian còn lại trước khi hết hạn (phút)
    TIMESTAMPDIFF(MINUTE, NOW(), fr.expires_at) AS minutes_remaining,
    CONCAT(
        '[ACTIVE] Ngập ', UPPER(fr.severity_level),
        ' | Còn ', TIMESTAMPDIFF(MINUTE, NOW(), fr.expires_at), ' phút',
        CASE WHEN fr.is_verified THEN ' ✓' ELSE '' END
    )                                           AS display_label
FROM `flood_reports` fr
WHERE fr.expires_at IS NULL                     -- Không có hạn = luôn hiển thị
   OR fr.expires_at > NOW()                     -- Chưa hết hạn
ORDER BY fr.severity_level DESC, fr.reported_at DESC;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  VIEW 3: v_flood_verified_spatial — Chỉ điểm ngập ĐÃ ĐƯỢC ADMIN DUYỆT ║
-- ║                                                                          ║
-- ║  Admin dùng view này để kiểm tra những điểm đã xác minh.                ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

DROP VIEW IF EXISTS `v_flood_verified_spatial`;

CREATE VIEW `v_flood_verified_spatial` AS
SELECT
    fr.id                                       AS report_id,
    fr.location                                 AS flood_point,
    ST_X(fr.location)                           AS latitude,
    ST_Y(fr.location)                           AS longitude,
    fr.severity_level,
    fr.reported_at,
    fr.expires_at,
    CONCAT(
        '[VERIFIED ✓] Ngập ', UPPER(fr.severity_level),
        ' tại (', ROUND(ST_X(fr.location), 5), ', ', ROUND(ST_Y(fr.location), 5), ')',
        ' | ', DATE_FORMAT(fr.reported_at, '%d/%m/%Y %H:%i')
    )                                           AS display_label
FROM `flood_reports` fr
WHERE fr.is_verified = TRUE
ORDER BY fr.reported_at DESC;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  VIEW 4: v_flood_severity_spatial — Phân nhóm theo mức độ ngập         ║
-- ║                                                                          ║
-- ║  Giúp Admin nhìn tổng quan thống kê theo từng cấp độ ngập.             ║
-- ║  Kết hợp với Spatial View để thấy phân bố không gian.                   ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

DROP VIEW IF EXISTS `v_flood_severity_spatial`;

CREATE VIEW `v_flood_severity_spatial` AS
SELECT
    fr.id                                       AS report_id,
    fr.location                                 AS flood_point,
    ST_X(fr.location)                           AS latitude,
    ST_Y(fr.location)                           AS longitude,
    fr.severity_level,
    -- Phân loại màu sắc gợi ý (tham chiếu khi hiển thị trên Frontend)
    CASE fr.severity_level
        WHEN 'low'    THEN '#FFC107'            -- Vàng (cảnh báo nhẹ)
        WHEN 'medium' THEN '#FF9800'            -- Cam (cảnh báo trung bình)
        WHEN 'high'   THEN '#F44336'            -- Đỏ (cảnh báo nghiêm trọng)
    END                                         AS severity_color,
    CASE fr.severity_level
        WHEN 'low'    THEN 'Mắt cá chân (≤20cm)'
        WHEN 'medium' THEN 'Nửa bánh xe (20-40cm)'
        WHEN 'high'   THEN 'Lút bánh xe (>40cm)'
    END                                         AS severity_description,
    fr.reported_at,
    fr.is_verified
FROM `flood_reports` fr
ORDER BY
    FIELD(fr.severity_level, 'high', 'medium', 'low'),
    fr.reported_at DESC;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  VIEW 5: v_traffic_spatial — Trực quan hóa điểm kẹt xe (nếu có bảng)  ║
-- ║                                                                          ║
-- ║  Chỉ tạo nếu bảng traffic_reports đã tồn tại (chạy 002 trước).         ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

DROP VIEW IF EXISTS `v_traffic_spatial`;

CREATE VIEW `v_traffic_spatial` AS
SELECT
    tr.id                                       AS report_id,
    tr.location                                 AS traffic_point,
    ST_X(tr.location)                           AS latitude,
    ST_Y(tr.location)                           AS longitude,
    tr.congestion_level,
    tr.description,
    tr.reported_at,
    tr.is_verified,
    tr.expires_at,
    CONCAT(
        'Kẹt xe [', UPPER(tr.congestion_level), ']',
        CASE WHEN tr.description IS NOT NULL
             THEN CONCAT(' - ', LEFT(tr.description, 50))
             ELSE '' END,
        ' | ', DATE_FORMAT(tr.reported_at, '%d/%m/%Y %H:%i')
    )                                           AS display_label
FROM `traffic_reports` tr
ORDER BY tr.reported_at DESC;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  VIEW 6: v_all_reports_spatial — Tổng hợp NGẬP + KẸT XE               ║
-- ║                                                                          ║
-- ║  Gộp cả 2 loại báo cáo để hiển thị toàn bộ trên 1 Spatial View.       ║
-- ║  Admin có thể thấy bức tranh tổng thể tình hình giao thông TPHCM.      ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

DROP VIEW IF EXISTS `v_all_reports_spatial`;

CREATE VIEW `v_all_reports_spatial` AS
SELECT
    CONCAT('FLOOD-', fr.id)                     AS report_id,
    'flood'                                     AS report_type,
    fr.location                                 AS report_point,
    ST_X(fr.location)                           AS latitude,
    ST_Y(fr.location)                           AS longitude,
    fr.severity_level                           AS level,
    fr.reported_at,
    fr.is_verified,
    fr.expires_at,
    CONCAT('🌊 Ngập ', UPPER(fr.severity_level))  AS display_label
FROM `flood_reports` fr
WHERE fr.expires_at IS NULL OR fr.expires_at > NOW()

UNION ALL

SELECT
    CONCAT('TRAFFIC-', tr.id)                   AS report_id,
    'traffic'                                   AS report_type,
    tr.location                                 AS report_point,
    ST_X(tr.location)                           AS latitude,
    ST_Y(tr.location)                           AS longitude,
    tr.congestion_level                         AS level,
    tr.reported_at,
    tr.is_verified,
    tr.expires_at,
    CONCAT('🚗 Kẹt xe ', UPPER(tr.congestion_level)) AS display_label
FROM `traffic_reports` tr
WHERE tr.expires_at IS NULL OR tr.expires_at > NOW()

ORDER BY reported_at DESC;


-- ╔════════════════════════════════════════════════════════════════════════════╗
-- ║  XÁC NHẬN: Liệt kê tất cả VIEW đã tạo trong database                  ║
-- ╚════════════════════════════════════════════════════════════════════════════╝

SELECT TABLE_NAME AS view_name, VIEW_DEFINITION
FROM INFORMATION_SCHEMA.VIEWS
WHERE TABLE_SCHEMA = 'flood_warning_db'
ORDER BY TABLE_NAME;

