# HỆ THỐNG BẢN ĐỒ CẢNH BÁO KẸT XE & NGẬP LỤT TP.HCM
### Real-Time Traffic Congestion & Flood Warning Map System (OpenFreeMap & MySQL Spatial)

Dự án cung cấp giải pháp bản đồ số hỗ trợ người dân theo dõi tình trạng kẹt xe theo thời gian thực, cập nhật các điểm ngập lụt từ cộng đồng (Crowdsourcing) và tìm kiếm lộ trình di chuyển né ngập an toàn tại TP. Hồ Chí Minh.

---

## 📌 TÍNH NĂNG NỔI BẬT

1. **Bản đồ số không cần API Key:** Sử dụng **OpenFreeMap** và thư viện **MapLibre GL JS** kết xuất vector mượt mà, không giới hạn lượt truy cập.
2. **Cảnh báo kẹt xe thời gian thực:** Tích hợp lớp giao thông (Traffic Flow) hiển thị màu sắc theo mật độ xe lưu thông.
3. **Quản lý điểm ngập lụt không gian (Spatial Data):**
   - Lưu trữ tọa độ chuẩn **POINT SRID 4326** trên **MySQL 8.0+**.
   - Chỉ mục không gian **SPATIAL INDEX (R-Tree)** giúp truy vấn cực nhanh (< 200ms).
   - Phân cấp 3 mức ngập theo SRS: `low` (Mắt cá chân), `medium` (Nửa bánh xe), `high` (Lút bánh xe).
4. **Phân tích lộ trình né ngập:** Giải mã đường đi (Polyline) và chạy thuật toán giao cắt không gian `ST_Intersects` & `ST_Distance_Sphere` để cảnh báo điểm ngập nằm trong phạm vi lộ trình.
5. **Cổng tiếp nhận báo cáo từ người dân (Crowdsourcing):** Hỗ trợ chọn điểm trực tiếp trên bản đồ hoặc định vị GPS với cơ chế chống spam (Rate Limiting).
6. **Hệ thống tài liệu API tự động:** Tích hợp sẵn chuẩn OpenAPI với **Swagger UI** và **ReDoc**.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2.0, PyMySQL, Uvicorn.
- **Database:** MySQL 8.0+ hỗ trợ Spatial Data & SPATIAL INDEX.
- **Frontend:** HTML5, Modern CSS (Responsive/Mobile-first), Vanilla JavaScript (ES6+), MapLibre GL JS.
- **Bản đồ nền:** OpenFreeMap (Liberty, Bright, Positron styles).
- **Kiểm thử & Tài liệu:** Postman Test Suite, Swagger UI, ReDoc.

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY HỆ THỐNG

### 1. Yêu cầu hệ thống
- **Python:** Phiên bản `>= 3.10`
- **MySQL Server:** Phiên bản `>= 8.0` (cần cài đặt và chạy dịch vụ MySQL)
- **Git** (nếu clone từ repository)

### 2. Cài đặt môi trường Backend
Mở Terminal / PowerShell tại thư mục gốc của dự án:

```powershell
# Bước 1: Tạo môi trường ảo Python (khuyến nghị)
python -m venv venv

# Bước 2: Kích hoạt môi trường ảo
# Trên Windows:
.\venv\Scripts\activate
# Trên Linux/macOS:
source venv/bin/activate

# Bước 3: Cài đặt tất cả các gói phụ thuộc
pip install -r requirements.txt
```

### 3. Cấu hình Cơ sở dữ liệu (.env)
1. Sao chép file cấu hình mẫu `.env.example` thành `.env`:
   ```powershell
   Copy-Item .env.example .env   # Trên Windows PowerShell
   # hoặc: cp .env.example .env  # Trên Linux/macOS
   ```
2. Mở file `.env` và điều chỉnh thông tin kết nối MySQL:
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=flood_warning_db
   DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/flood_warning_db?charset=utf8mb4
   ```
3. Tạo Database trong MySQL:
   ```sql
   CREATE DATABASE IF NOT EXISTS flood_warning_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
4. Khởi tạo cấu trúc bảng và chỉ mục không gian (SPATIAL INDEX):
   ```powershell
   python -m backend.app.db.init_db
   ```

### 4. Khởi động Backend Server
Chạy máy chủ FastAPI với Uvicorn:
```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Server sẽ chạy tại: `http://127.0.0.1:8000`

### 5. Khởi động Frontend
Ứng dụng Frontend là mã nguồn Web tĩnh (Static Web), có thể khởi chạy bằng nhiều cách:
- **Cách 1 (Dùng Python HTTP Server):**
  ```powershell
  python -m http.server 5500 -d frontend
  ```
  Truy cập tại: `http://127.0.0.1:5500`
- **Cách 2 (Dùng VS Code Live Server):** Nhấp chuột phải vào file `frontend/index.html` và chọn **"Open with Live Server"**.

---

## 📖 TÀI LIỆU API TỰ ĐỘNG (FASTAPI SWAGGER UI & REDOC)

FastAPI tự động sinh tài liệu API động dựa trên OpenAPI 3.0 với đầy đủ mô tả `summary`, `status_code`, tham số và ví dụ mẫu:

- **Swagger UI (Tương tác trực tiếp, chạy thử API):**  
  👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Giao diện tài liệu chuẩn chuyên nghiệp):**  
  👉 [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Danh mục các nhóm API chính trong hệ thống:

| Nhóm API | Method | Endpoint | Summary & Chức năng | Status Codes |
| :--- | :---: | :--- | :--- | :---: |
| **Floods** | `GET` | `/api/v1/floods` | Lấy danh sách các điểm đang ngập còn hiệu lực tại TP.HCM | `200`, `500` |
| **Floods** | `POST` | `/api/v1/floods` | Người dân gửi báo cáo điểm ngập mới (Crowdsourcing) | `201`, `422`, `429`, `500` |
| **Floods** | `POST` | `/api/v1/floods/cleanup` | Kích hoạt tác vụ dọn dẹp / hạ cấp điểm ngập hết hạn | `200`, `500` |
| **Routes** | `POST` | `/api/v1/routes/check-flood` | Kiểm tra lộ trình giao cắt vùng ngập (`ST_Intersects`) | `200`, `400`, `500` |
| **Admin** | `GET` | `/api/v1/admin/floods` | Admin: Xem toàn bộ danh sách điểm ngập (kể cả chưa duyệt) | `200`, `500` |
| **Admin** | `POST` | `/api/v1/admin/floods` | Admin: Thêm trực tiếp điểm ngập đã xác minh | `201`, `422`, `500` |
| **Admin** | `PATCH` | `/api/v1/admin/floods/{id}/verify` | Admin: Duyệt báo cáo của người dân (`is_verified = True`) | `200`, `404` |
| **Admin** | `PUT` | `/api/v1/admin/floods/{id}` | Admin: Hiệu chỉnh tọa độ và mức ngập | `200`, `404`, `422` |
| **Admin** | `DELETE` | `/api/v1/admin/floods/{id}` | Admin: Xóa điểm ngập khỏi CSDL | `200`, `404` |
| **Traffic** | `GET` | `/api/v1/traffic/flow/{z}/{x}/{y}.png` | Proxy tải tile mật độ giao thông vệ tinh thời gian thực | `200`, `404`, `502`, `503` |
| **Config** | `GET` | `/api/v1/config` | Lấy cấu hình OpenFreeMap và ranh giới TP.HCM | `200` |
| **Health** | `GET` | `/health` | Kiểm tra trạng thái hoạt động của Backend và MySQL | `200`, `503` |

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
traffic-flood-hcm-project/
├── backend/
│   ├── app/
│   │   ├── core/           # Cấu hình hệ thống, logging, rate limiter, cleanup
│   │   ├── db/             # Kết nối SQLAlchemy engine & script khởi tạo bảng
│   │   ├── middleware/     # CORS, Request logging, Rate limiter
│   │   ├── models/         # SQLAlchemy Models (FloodReport, Spatial Point)
│   │   ├── routers/        # Định nghĩa các Endpoint API (OpenAPI tags, summary, status)
│   │   ├── schemas/        # Pydantic Schemas xác thực dữ liệu vào/ra
│   │   ├── services/       # Nghiệp vụ xử lý (CRUD, Spatial Query Route Service)
│   │   └── main.py         # Entry point khởi tạo ứng dụng FastAPI
├── frontend/
│   ├── css/
│   │   └── style.css       # Giao diện Modern UI, Mobile-first, animations
│   ├── js/
│   │   ├── app.js          # Điều phối chính, Toast & Loading Spinner
│   │   ├── config.js       # Cấu hình tọa độ TP.HCM & style OpenFreeMap
│   │   ├── floods.js       # Quản lý marker & danh sách điểm ngập
│   │   ├── map.js          # Khởi tạo MapLibre GL JS & định vị GPS
│   │   ├── report.js       # Báo cáo điểm ngập cộng đồng
│   │   └── routing.js      # Tính toán đường đi & cảnh báo né ngập
│   └── index.html          # Giao diện chính của ứng dụng
├── docs/
│   ├── ADMIN_WORKBENCH_SPATIAL_GUIDE.md  # Quy trình Admin duyệt & thao tác MySQL Workbench
│   └── API_TEST_CASES_REPORT.md          # Báo cáo Test Cases & hiệu năng API (< 200ms)
├── .env.example            # Mẫu file cấu hình môi trường
├── postman_collection.json # Bộ sưu tập kiểm thử tự động API bằng Postman
├── requirements.txt        # Danh sách thư viện Python cần thiết
└── README.md               # Tài liệu tổng quan & hướng dẫn cài đặt hệ thống
```

---

## 📑 TÀI LIỆU LIÊN QUAN

- [Quy trình Quản trị & Thao tác dữ liệu không gian qua MySQL Workbench](file:///c:/Users/dell%205620/Documents/traffic-flood-hcm-project/docs/ADMIN_WORKBENCH_SPATIAL_GUIDE.md)
- [Báo cáo Kiểm thử toàn bộ API & Phân tích hiệu năng < 200ms](file:///c:/Users/dell%205620/Documents/traffic-flood-hcm-project/docs/API_TEST_CASES_REPORT.md)
