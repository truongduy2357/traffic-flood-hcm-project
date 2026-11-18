
from datetime import datetime

from app.models.flood_report import FloodReport, SeverityLevel
from app.schemas.flood_report import FloodReportResponse


# Tạo một FloodReport mẫu, không cần kết nối MySQL
report = FloodReport(
    id=1,
    location="POINT(10.776889 106.700806)",
    severity_level=SeverityLevel.LOW,
    reported_at=datetime.now(),
    is_verified=False,
    expires_at=None,
)

# Chuyển SQLAlchemy Model thành Pydantic Response
response = FloodReportResponse.model_validate(report)

# Xuất dữ liệu JSON
json_data = response.model_dump()

print("JSON RESPONSE:")
print(response.model_dump_json(indent=2))

# Kiểm tra tọa độ
assert json_data["latitude"] == 10.776889
assert json_data["longitude"] == 106.700806
assert json_data["coordinates"] == [10.776889, 106.700806]

print("\nMODEL TO JSON: ALL TESTS PASSED!")
