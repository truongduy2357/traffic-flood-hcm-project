
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limiter import (
    RateLimitMiddleware,
    _ip_request_history,
)

app = FastAPI()

app.add_middleware(
    RateLimitMiddleware,
    max_requests=60,
    window_seconds=60,
)


@app.post("/api/v1/floods")
def create_flood():
    return {"message": "Report created"}


# Xóa lịch sử request cũ để test độc lập
_ip_request_history.clear()

client = TestClient(app)

# 10 request đầu phải được phép
for i in range(10):
    response = client.post("/api/v1/floods")
    print(f"Request {i + 1}: {response.status_code}")
    assert response.status_code == 200

# Request thứ 11 phải bị chặn
response = client.post("/api/v1/floods")

print("Request 11:", response.status_code)
print("Response:", response.json())

assert response.status_code == 429

print("\nALL RATE LIMIT TESTS PASSED!")
