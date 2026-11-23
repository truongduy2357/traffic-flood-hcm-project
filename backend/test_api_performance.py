"""
Script kiểm thử tự động toàn bộ API và đo thời gian phản hồi (< 200ms)
Dự án: Hệ thống Bản đồ Cảnh báo Kẹt xe & Ngập lụt TPHCM
Sprint 4 - Tiêu chuẩn hiệu năng SRS: Thời gian phản hồi < 200ms
"""

import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

# Cấu hình địa chỉ Backend
BASE_URL = "http://127.0.0.1:8000"

# Danh sách 12 Test Cases chuẩn kiểm thử toàn diện
TEST_CASES = [
    {
        "id": "TC-01",
        "name": "Health Check hệ thống",
        "method": "GET",
        "path": "/health",
        "body": None,
        "expected_status": [200],
    },
    {
        "id": "TC-02",
        "name": "Lấy cấu hình bản đồ OpenFreeMap",
        "method": "GET",
        "path": "/api/v1/config",
        "body": None,
        "expected_status": [200],
    },
    {
        "id": "TC-03",
        "name": "Kiểm tra trang chủ API Root",
        "method": "GET",
        "path": "/",
        "body": None,
        "expected_status": [200],
    },
    {
        "id": "TC-04",
        "name": "Lấy danh sách điểm ngập đang hoạt động",
        "method": "GET",
        "path": "/api/v1/floods",
        "body": None,
        "expected_status": [200],
    },
    {
        "id": "TC-05",
        "name": "Báo cáo điểm ngập mới (Người dân)",
        "method": "POST",
        "path": "/api/v1/floods",
        "body": {
            "title": "Đường Nguyễn Hữu Cảnh, Bình Thạnh (Test)",
            "description": "Nước ngập nửa bánh xe",
            "latitude": 10.7932,
            "longitude": 106.7214,
            "severity_level": "medium",
            "water_depth_cm": 30,
            "radius_meters": 50,
        },
        "expected_status": [200, 201],
    },
    {
        "id": "TC-06",
        "name": "Báo cáo ngập ngoài TP.HCM (Kiểm tra validate)",
        "method": "POST",
        "path": "/api/v1/floods",
        "body": {
            "title": "Tọa độ ngoài TP.HCM",
            "latitude": 21.0285,
            "longitude": 105.8542,
            "severity_level": "high",
        },
        "expected_status": [422],
    },
    {
        "id": "TC-07",
        "name": "Kiểm tra lộ trình né ngập qua Polyline",
        "method": "POST",
        "path": "/api/v1/routes/check-flood",
        "body": {
            "encoded_polyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
            "buffer_meters": 50,
        },
        "expected_status": [200],
    },
    {
        "id": "TC-08",
        "name": "Kiểm tra lộ trình qua danh sách điểm GPS",
        "method": "POST",
        "path": "/api/v1/routes/check-flood",
        "body": {
            "points": [
                {"latitude": 10.7769, "longitude": 106.7009},
                {"latitude": 10.7932, "longitude": 106.7214},
            ],
            "buffer_meters": 50,
        },
        "expected_status": [200],
    },
    {
        "id": "TC-09",
        "name": "Admin: Xem danh sách toàn bộ điểm ngập",
        "method": "GET",
        "path": "/api/v1/admin/floods?limit=20",
        "body": None,
        "expected_status": [200],
    },
    {
        "id": "TC-10",
        "name": "Admin: Thêm điểm ngập quản trị",
        "method": "POST",
        "path": "/api/v1/admin/floods",
        "body": {
            "title": "Đường Huỳnh Tấn Phát, Quận 7 (Admin Test)",
            "latitude": 10.7428,
            "longitude": 106.7325,
            "severity_level": "high",
            "water_depth_cm": 50,
            "radius_meters": 70,
        },
        "expected_status": [200, 201],
    },
    {
        "id": "TC-11",
        "name": "Kích hoạt dọn dẹp điểm ngập hết hạn",
        "method": "POST",
        "path": "/api/v1/floods/cleanup",
        "body": None,
        "expected_status": [200],
    },
    {
        "id": "TC-12",
        "name": "Lấy tile giao thông TomTom qua proxy",
        "method": "GET",
        "path": "/api/v1/traffic/flow/12/3261/1976.png",
        "body": None,
        "expected_status": [200, 503],
    },
]


def run_single_test(tc, base_url=BASE_URL):
    url = f"{base_url}{tc['path']}"
    headers = {"User-Agent": "FastAPI-Performance-Tester/1.0"}
    data = None

    if tc["body"] is not None:
        data = json.dumps(tc["body"]).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=tc["method"])

    start_time = time.perf_counter()
    status_code = None
    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            status_code = response.getcode()
            response.read()
    except urllib.error.HTTPError as e:
        status_code = e.code
        e.read()
    except Exception as e:
        return {
            "id": tc["id"],
            "name": tc["name"],
            "method": tc["method"],
            "status": "CONNECTION_ERROR",
            "code": None,
            "time_ms": 0,
            "passed": False,
            "error": str(e),
        }

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    is_status_ok = status_code in tc["expected_status"]
    is_time_ok = elapsed_ms < 200.0  # Tiêu chuẩn SRS: < 200ms

    return {
        "id": tc["id"],
        "name": tc["name"],
        "method": tc["method"],
        "status": status_code,
        "time_ms": round(elapsed_ms, 2),
        "is_status_ok": is_status_ok,
        "is_time_ok": is_time_ok,
        "passed": is_status_ok and is_time_ok,
    }


def main():
    print("=" * 80)
    print(" BỘ KIỂM THỬ TỰ ĐỘNG HIỆU NĂNG TOÀN BỘ REST API (SPRINT 4)")
    print(" Tiêu chí: Mã phản hồi hợp lệ & Thời gian phản hồi < 200ms")
    print(f" Mục tiêu kiểm thử: {BASE_URL}")
    print("=" * 80)

    # 1. Kiểm tra server có đang chạy không
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2.0) as resp:
            pass
    except Exception:
        print("\n [!] Máy chủ Backend FastAPI chưa chạy tại http://127.0.0.1:8000")
        print("  -> Vui lòng chạy lệnh sau ở một cửa sổ dòng lệnh riêng để bật server:")
        print("     uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload")
        print("\n Sau khi server chạy, chạy lại file này để đo hiệu năng thực tế.")
        print("=" * 80)
        return

    # 2. Chạy từng test case và ghi nhận kết quả
    results = []
    print(f"\n{'ID':<7} | {'METHOD':<6} | {'THỜI GIAN':<12} | {'MÃ HTTP':<8} | {'TIÊU CHUẨN <200ms':<18} | {'TÊN TEST CASE'}")
    print("-" * 80)

    all_passed = True
    for tc in TEST_CASES:
        res = run_single_test(tc)
        results.append(res)

        status_str = f"{res['status']}" if res['status'] else "ERR"
        time_str = f"{res['time_ms']} ms"
        time_check = " PASS (<200ms)" if res.get("is_time_ok") else " FAIL (>=200ms)"
        if not res["passed"]:
            all_passed = False

        print(f"{res['id']:<7} | {res['method']:<6} | {time_str:<12} | {status_str:<8} | {time_check:<18} | {res['name']}")

    print("=" * 80)
    avg_time = sum(r["time_ms"] for r in results) / len(results) if results else 0
    print(f" TỔNG KẾT: {len(results)}/{len(results)} Test Cases đã thực hiện.")
    print(f" Thời gian phản hồi trung bình: {avg_time:.2f} ms")
    if all_passed:
        print(" TẤT CẢ API ĐỀU ĐẠT TIÊU CHUẨN HIỆU NĂNG < 200ms THEO ĐẶC TẢ SRS!")
    else:
        print(" [!] Có một số test case chưa đạt yêu cầu.")
    print("=" * 80)


if __name__ == "__main__":
    main()
