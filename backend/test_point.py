from app.models.spatial import create_point_wkt, parse_point_wkt


# Test 1: Tạo WKT
wkt = create_point_wkt(10.776889, 106.700806)
print("WKT:", wkt)

# Test 2: Chuyển WKT thành tọa độ
lat, lng = parse_point_wkt(wkt)
print("Coordinates:", [lat, lng])

assert lat == 10.776889
assert lng == 106.700806

# Test 3: Dữ liệu không hợp lệ
assert parse_point_wkt("INVALID") == (None, None)

# Test 4: Dữ liệu rỗng
assert parse_point_wkt(None) == (None, None)

# Test 5: Vĩ độ vượt giới hạn
assert parse_point_wkt("POINT(100 106.7)") == (None, None)

# Test 6: Kinh độ vượt giới hạn
assert parse_point_wkt("POINT(10 200)") == (None, None)

print("ALL TESTS PASSED!")
