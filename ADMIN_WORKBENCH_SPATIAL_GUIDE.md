# TÀI LIỆU QUY TRÌNH QUẢN TRỊ, DUYỆT VÀ THAO TÁC TRỰC TIẾP DỮ LIỆU KHÔNG GIAN QUA MYSQL WORKBENCH
## DỰ ÁN: HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE & NGẬP LỤT TP.HCM
**Tài liệu chuẩn vận hành nội bộ dành cho Quản trị viên (Admin / DBA)**  
**Áp dụng:** Hệ thống Cơ sở dữ liệu Không gian MySQL 8.0+ (SRID 4326)

---

## 1. TỔNG QUAN & MỤC ĐÍCH TÀI LIỆU

### 1.1. Mục đích
Tài liệu này quy định và hướng dẫn chi tiết quy trình chuẩn dành cho Quản trị viên (Admin/DBA) trong việc:
1. **Kiểm duyệt báo cáo điểm ngập:** Xác minh, xử lý các phản ánh điểm ngập lụt do người dân gửi lên (Crowdsourcing) trước khi hiển thị rộng rãi trên bản đồ công cộng.
2. **Thao tác trực tiếp với dữ liệu không gian (Spatial Data):** Thêm mới, tra cứu, chỉnh sửa tọa độ và mức độ ngập lụt trực tiếp trên công cụ **MySQL Workbench** mà không cần thông qua giao diện Web.
3. **Trực quan hóa không gian:** Tận dụng tính năng **Spatial Data Viewer** tích hợp sẵn của MySQL Workbench để quan sát các điểm ngập trên bản đồ hình học.
4. **Bảo đảm toàn vẹn chỉ mục không gian (Spatial Index):** Duy trì hiệu năng truy vấn không gian cực nhanh (< 200ms) theo yêu cầu đặc tả SRS.

### 1.2. Vị trí lưu trữ file
- **Đường dẫn chuẩn trong kho dự án:** `docs/ADMIN_WORKBENCH_SPATIAL_GUIDE.md`
- **Đường dẫn sao lưu thư mục gốc:** `ADMIN_WORKBENCH_SPATIAL_GUIDE.md`

---

## 2. THIẾT LẬP MÔI TRƯỜNG & KẾT NỐI TRÊN MYSQL WORKBENCH

### 2.1. Thông số kết nối cơ sở dữ liệu
Quản trị viên khởi động MySQL Workbench và tạo kết nối mới (New Connection):
- **Connection Name:** `HCM_Traffic_Flood_DB`
- **Hostname:** `localhost` (hoặc IP máy chủ Database)
- **Port:** `3306`
- **Username:** `root` (hoặc tài khoản admin được cấp phát)
- **Default Schema:** `flood_warning_db`

### 2.2. Cấu hình "Safe Updates" trong MySQL Workbench
Mặc định MySQL Workbench bật chế độ chặn `UPDATE`/`DELETE` khi câu lệnh không có khóa chính (`WHERE id = ...`). Để thao tác mượt mà trong việc xử lý hàng loạt:
1. Mở menu **Edit** -> chọn **Preferences...** (trên macOS: **MySQL Workbench** -> **Preferences**).
2. Chọn thẻ **SQL Editor**.
3. Cuộn xuống phần **Other**, bỏ tích chọn: `Safe Updates (rejects UPDATEs and DELETEs with no restrictions)`.
4. Nhấn **OK** và mở lại tab truy vấn mới để áp dụng.
*(Hoặc có thể gõ trực tiếp trong tab Query: `SET SQL_SAFE_UPDATES = 0;`).*

---

## 3. ĐẶC TẢ CẤU TRÚC DỮ LIỆU KHÔNG GIAN BẢNG `flood_reports`

### 3.1. Lược đồ bảng (Schema Definition)
Bảng lưu trữ thông tin không gian chính của dự án là `flood_reports`:

| Tên cột | Kiểu dữ liệu | Ràng buộc | Ý nghĩa nghiệp vụ |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | `PRIMARY KEY, AUTO_INCREMENT` | Định danh duy nhất điểm ngập |
| `location` | `POINT SRID 4326` | `NOT NULL` | Tọa độ GPS chuẩn WGS 84 (`POINT(lat lng)`) |
| `severity_level` | `ENUM('low', 'medium', 'high')` | `NOT NULL, DEFAULT 'low'` | Mức độ ngập: `low` (mắt cá chân 10-20cm), `medium` (nửa bánh 20-40cm), `high` (lút bánh >40cm) |
| `reported_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm ghi nhận báo cáo |
| `is_verified` | `TINYINT(1) / BOOLEAN` | `NOT NULL, DEFAULT 0` | Trạng thái duyệt: `0` (Chờ duyệt), `1` (Đã duyệt) |
| `expires_at` | `DATETIME` | `NULL` | Thời điểm điểm ngập tự động hết hạn |

### 3.2. Quy ước quan trọng về Hệ quy chiếu SRID 4326 & Trục tọa độ
> [!IMPORTANT]
> **Quy ước trục tọa độ:**
> Trong MySQL 8.0+, hệ tọa độ WGS 84 (SRID 4326) có thứ tự trục mặc định là `(Latitude, Longitude)` tức `(Vĩ độ, Kinh độ)`.
> - Định dạng WKT chuẩn khi thao tác: `POINT(vĩ_độ kinh_độ)`
> - Ranh giới hợp lệ TP.HCM:
>   - **Vĩ độ (Latitude):** `10.37` đến `11.16`
>   - **Kinh độ (Longitude):** `106.35` đến `106.93`
> - Ví dụ tọa độ chuẩn tại trung tâm Quận 1: `POINT(10.776889 106.700806)`

---

## 4. QUY TRÌNH KIỂM DUYỆT BÁO CÁO NGẬP (CROWDSOURCING VERIFICATION)

Mỗi khi người dân gửi báo cáo qua ứng dụng di động/web, bản ghi được tạo với `is_verified = 0`. Admin thực hiện duyệt theo 5 bước sau:

```
[Báo cáo từ dân] ➔ [1. Truy vấn is_verified = 0] ➔ [2. Xem Spatial Viewer] ➔ [3. Đối chiếu ranh giới & thực tế] ➔ [4. Phê duyệt (SET 1) HOẶC Từ chối (DELETE)]
```

### Bước 1: Lọc danh sách báo cáo đang chờ kiểm duyệt
Mở tab SQL Query trong Workbench và thực thi:
```sql
USE flood_warning_db;

-- Lấy danh sách điểm ngập chờ duyệt kèm tọa độ dạng chuỗi Text dễ đọc
SELECT 
    id,
    ST_AsText(location) AS wkt_location,
    ST_Latitude(location) AS latitude,
    ST_Longitude(location) AS longitude,
    severity_level,
    reported_at,
    expires_at,
    is_verified
FROM flood_reports
WHERE is_verified = 0
ORDER BY reported_at DESC;
```

### Bước 2: Trực quan hóa điểm ngập trên bản đồ MySQL Workbench (Spatial Viewer)
Để quan sát vị trí hình học của các điểm ngập:
1. Chạy câu lệnh truy vấn trả về trực tiếp cột `location`:
   ```sql
   SELECT id, location, severity_level, is_verified 
   FROM flood_reports 
   WHERE is_verified = 0;
   ```
2. Trong bảng kết quả **Result Grid**, tại góc bên phải thanh công cụ của bảng kết quả, nhấp vào biểu tượng **Spatial Viewer** (hoặc chuyển thẻ từ `Form View` / `Field Data` sang thẻ `Spatial Viewer`).
3. MySQL Workbench sẽ hiển thị bản đồ trực quan tọa độ không gian các điểm ngập:
   - Các điểm phân bố theo hình học 2D.
   - Nhấp vào từng điểm để xem thuộc tính chi tiết.

### Bước 3: Đánh giá và kiểm tra tính hợp lệ
Admin đối chiếu các tiêu chí an toàn:
1. **Kiểm tra ranh giới:** Tọa độ có nằm trong phạm vi địa lý TP.HCM không?
   - Vĩ độ: `10.37 <= Latitude <= 11.16`
   - Kinh độ: `106.35 <= Longitude <= 106.93`
2. **Kiểm tra trùng lặp (Duplicate Detection):** Có điểm ngập nào khác đã tồn tại trong bán kính 50 mét hay không? (Sử dụng hàm tính khoảng cách ở Mục 5.3).
3. **Mức độ ngập:** Kiểm tra tính hợp lý của `severity_level`.

### Bước 4: Thực hiện Phê duyệt (Approve)
Khi báo cáo chính xác, Admin xác nhận duyệt và đặt thời gian hết hạn (ví dụ có hiệu lực trong vòng 24 giờ kể từ thời điểm duyệt):
```sql
-- Phê duyệt điểm ngập có ID cụ thể (ví dụ ID = 15)
UPDATE flood_reports
SET 
    is_verified = 1,
    expires_at = DATE_ADD(NOW(), INTERVAL 24 HOUR)
WHERE id = 15;
```

Nếu muốn phê duyệt hàng loạt các điểm ngập hợp lệ trong hôm nay:
```sql
UPDATE flood_reports
SET 
    is_verified = 1,
    expires_at = DATE_ADD(NOW(), INTERVAL 24 HOUR)
WHERE is_verified = 0 
  AND reported_at >= CURDATE()
  AND ST_Latitude(location) BETWEEN 10.37 AND 11.16
  AND ST_Longitude(location) BETWEEN 106.35 AND 106.93;
```

### Bước 5: Từ chối hoặc xóa báo cáo rác (Reject / Delete)
Nếu thông tin sai sự thật, nằm ngoài TP.HCM hoặc là dữ liệu spam:
```sql
-- Xóa báo cáo rác/sai sự thật
DELETE FROM flood_reports
WHERE id = 15 AND is_verified = 0;
```

---

## 5. CẨM NANG THAO TÁC TRỰC TIẾP DỮ LIỆU KHÔNG GIAN (SPATIAL CRUD)

Dành cho các trường hợp khẩn cấp, Admin cập nhật điểm ngập trực tiếp qua SQL mà không cần bật Web.

### 5.1. Thêm mới thủ công điểm ngập khẩn cấp (Spatial INSERT)
Khi có cảnh báo ngập từ cơ quan chức năng hoặc đài khí tượng thủy văn:
```sql
-- Thêm điểm ngập tại Đường Nguyễn Hữu Cảnh, Bình Thạnh (Lat: 10.7932, Lng: 106.7214)
-- Mức ngập cao (high), tự động gắn cờ đã duyệt (is_verified = 1), hết hạn sau 12 giờ
INSERT INTO flood_reports (location, severity_level, is_verified, reported_at, expires_at)
VALUES (
    ST_GeomFromText('POINT(10.793200 106.721400)', 4326),
    'high',
    1,
    NOW(),
    DATE_ADD(NOW(), INTERVAL 12 HOUR)
);
```

> [!CAUTION]
> Luôn khai báo tham số SRID là `4326` trong hàm `ST_GeomFromText(..., 4326)`. Nếu bỏ quên tham số SRID, MySQL sẽ mặc định gán SRID 0 khiến câu lệnh INSERT bị lỗi hoặc vô hiệu hóa SPATIAL INDEX!

### 5.2. Hiệu chỉnh tọa độ và mức độ ngập (Spatial UPDATE)
Khi nước bắt đầu rút hoặc tọa độ ban đầu có sai lệch:
```sql
-- Trường hợp 1: Hạ mức ngập từ high xuống medium khi nước rút bớt
UPDATE flood_reports
SET 
    severity_level = 'medium',
    expires_at = DATE_ADD(NOW(), INTERVAL 6 HOUR)
WHERE id = 12;

-- Trường hợp 2: Hiệu chỉnh lại tọa độ chính xác của điểm ngập
UPDATE flood_reports
SET 
    location = ST_GeomFromText('POINT(10.795500 106.723000)', 4326)
WHERE id = 12;
```

### 5.3. Truy vấn không gian nâng cao (Spatial Queries)

#### A. Tìm tất cả các điểm ngập nằm trong bán kính R mét quanh 1 vị trí
Sử dụng hàm chuẩn không gian `ST_Distance_Sphere` (tính toán khoảng cách hình cầu theo mét trên Trái Đất):
```sql
-- Tìm tất cả các điểm ngập trong bán kính 1000 mét (1km) tính từ Chợ Bến Thành (10.7725, 106.6980)
SELECT 
    id,
    severity_level,
    ST_AsText(location) AS coordinates,
    ROUND(ST_Distance_Sphere(location, ST_GeomFromText('POINT(10.772500 106.698000)', 4326)), 2) AS distance_meters,
    is_verified,
    expires_at
FROM flood_reports
WHERE (expires_at IS NULL OR expires_at > NOW())
  AND ST_Distance_Sphere(location, ST_GeomFromText('POINT(10.772500 106.698000)', 4326)) <= 1000
ORDER BY distance_meters ASC;
```

#### B. Tìm các điểm ngập nằm trong vùng hình chữ nhật (Bounding Box - MBR)
```sql
-- Lọc các điểm ngập nằm trọn trong khu vực Quận 1 & Bình Thạnh
SELECT 
    id,
    severity_level,
    ST_AsText(location) AS coordinates
FROM flood_reports
WHERE MBRContains(
    ST_GeomFromText('POLYGON((10.75 106.68, 10.82 106.68, 10.82 106.75, 10.75 106.75, 10.75 106.68))', 4326),
    location
);
```

#### C. Thống kê số lượng điểm ngập theo từng mức độ
```sql
SELECT 
    severity_level,
    COUNT(*) AS total_points,
    SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) AS verified_points,
    SUM(CASE WHEN is_verified = 0 THEN 1 ELSE 0 END) AS pending_points
FROM flood_reports
WHERE expires_at IS NULL OR expires_at > NOW()
GROUP BY severity_level;
```

### 5.4. Dọn dẹp điểm ngập hết hạn (Maintenance Cleanup)
Khi nước đã rút hoàn toàn hoặc điểm ngập quá hạn thời gian:
```sql
-- Kiểm tra có bao nhiêu điểm ngập đã hết hạn
SELECT COUNT(*) AS expired_count
FROM flood_reports
WHERE expires_at IS NOT NULL AND expires_at <= NOW();

-- Thực hiện dọn dẹp các điểm ngập đã hết hạn quá 7 ngày để giải phóng dung lượng
DELETE FROM flood_reports
WHERE expires_at IS NOT NULL 
  AND expires_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

---

## 6. QUY TẮC AN TOÀN DỮ LIỆU & BẢO TRÌ SPATIAL INDEX

### 6.1. Luôn sử dụng Transaction khi cập nhật số lượng lớn
Trước khi thực hiện bất kỳ lệnh sửa đổi lớn nào, hãy bao bọc trong Transaction:
```sql
START TRANSACTION;

-- Thực hiện câu lệnh cập nhật
UPDATE flood_reports 
SET severity_level = 'low' 
WHERE is_verified = 1 AND reported_at < DATE_SUB(NOW(), INTERVAL 12 HOUR);

-- Kiểm tra lại số dòng bị ảnh hưởng
-- Nếu đúng kết quả mong muốn:
COMMIT;

-- Nếu sai sót hoặc cập nhật nhầm:
-- ROLLBACK;
```

### 6.2. Kiểm tra tính hợp lệ của Spatial Index
Để đảm bảo cây chỉ mục R-Tree luôn hoạt động tối ưu:
```sql
-- 1. Kiểm tra cấu trúc chỉ mục trên bảng flood_reports
SHOW INDEX FROM flood_reports;

-- Kết quả cần đảm bảo:
-- Key_name: 'idx_flood_reports_location'
-- Column_name: 'location'
-- Index_type: 'SPATIAL'

-- 2. Kiểm tra tính toàn vẹn vật lý của bảng
CHECK TABLE flood_reports;

-- 3. Tối ưu hóa lại cây chỉ mục không gian sau khi thêm/xóa nhiều dữ liệu
OPTIMIZE TABLE flood_reports;
```

### 6.3. Khắc phục lỗi thường gặp khi thao tác Spatial trên MySQL Workbench
| Mã lỗi / Hiện tượng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| `Error 3617: Latitude is out of range in function st_geomfromtext` | Nhập nhầm thứ tự `Longitude` trước `Latitude` (ví dụ `106.7 10.7`) | Đổi lại đúng chuẩn: `ST_GeomFromText('POINT(lat lng)', 4326)` |
| `Error 1416: Cannot get geometry object from data you send to the GEOMETRY field` | Thiếu hàm `ST_GeomFromText` hoặc sai định dạng WKT | Sử dụng cú pháp `ST_GeomFromText('POINT(x y)', 4326)` |
| `The target table cannot be opened because of spatial index error` | Có bản ghi có giá trị `location IS NULL` hoặc sai SRID | Đảm bảo cột `location` luôn có tọa độ hợp lệ, không chứa `NULL` |
| Bảng `Result Grid` hiển thị `BLOB` ở cột location | Workbench hiển thị dữ liệu nhị phân của trường hình học | Sử dụng `ST_AsText(location)` trong câu lệnh `SELECT` để đọc tọa độ |

---

## 7. CHECKLIST QUẢN TRỊ ĐỊNH KỲ CHO ADMIN

| Thời điểm | Nhiệm vụ Admin | Câu lệnh / Thao tác tương ứng |
| :---: | :--- | :--- |
| **Đầu mỗi ca trực** | Kiểm tra danh sách điểm ngập chờ duyệt | `SELECT * FROM flood_reports WHERE is_verified = 0;` |
| **Mỗi 4 giờ** | Rà soát các điểm ngập đang hoạt động, hạ cấp độ nếu nước rút | Cập nhật `severity_level` từ `high` ➔ `medium` ➔ `low` |
| **Cuối mỗi ngày** | Dọn dẹp dữ liệu rác, lưu trữ báo cáo cũ | Chạy câu lệnh dọn dẹp điểm ngập hết hạn |
| **Mỗi tuần** | Kiểm tra chỉ mục không gian & tối ưu hóa bảng | Chạy `CHECK TABLE` và `OPTIMIZE TABLE flood_reports;` |
| **Trước mỗi bản cập nhật** | Sao lưu dữ liệu dự phòng (Backup Database) | Dùng tính năng **Data Export** của MySQL Workbench xuất file `.sql` |

---
*Tài liệu được biên soạn phục vụ vận hành chính thức dự án Hệ thống Bản đồ Cảnh báo Kẹt xe và Ngập lụt TP.HCM.*
