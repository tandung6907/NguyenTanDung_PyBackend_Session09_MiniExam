from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Flight Manager API", version="1.0.0")

flights_db = [
    {
        "id": 1,
        "flight_number": "VN-213",
        "destination": "Da Nang",
        "available_seats": 45,
        "status": "scheduled",
    },
    {
        "id": 2,
        "flight_number": "VJ-122",
        "destination": "Phu Quoc",
        "available_seats": 12,
        "status": "scheduled",
    },
        {
        "id": 3,
        "flight_number": "VN-212",
        "destination": "tp. HCM",
        "available_seats": 18,
        "status": "delayed",
    },
        {
        "id": 2,
        "flight_number": "VJ-122",
        "destination": "Bac Kinh - Trung Quoc",
        "available_seats": 36,
        "status": "landed",
    },
]

# PYDANTIC SCHEMA
class FlightCreateRequest(BaseModel):
    flight_number: str = Field(
        ...,
        min_length=5,
        max_length=10,
        description="Số hiệu chuyến bay, độ dài từ 5 đến 10 ký tự",
    )
    destination: str = Field(
        ...,
        min_length=1,
        description="Điểm đến, không được để trống",
    )
    available_seats: int = Field(
        ...,
        ge=1,
        description="Số ghế trống, phải lớn hơn hoặc bằng 1",
    )

    @field_validator("destination")
    @classmethod
    def destination_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("destination không được để trống hoặc toàn khoảng trắng")
        return value.strip()


# HELPER: UNIFIED RESPONSE ENVELOPE
def build_envelope(status_code: int, message: str, data, error, path: str) -> dict:
    return {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "path": path,
    }


def get_next_id() -> int:
    if not flights_db:
        return 1
    return max(flight["id"] for flight in flights_db) + 1


def find_flight_by_number(flight_number: str) -> Optional[dict]:
    normalized = flight_number.strip().lower()
    for flight in flights_db:
        if flight["flight_number"].lower() == normalized:
            return flight
    return None


def find_flight_by_id(flight_id: int) -> Optional[dict]:
    for flight in flights_db:
        if flight["id"] == flight_id:
            return flight
    return None


# CUSTOM EXCEPTION HANDLER: chuẩn hóa lỗi HTTPException về đúng envelope
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "Đã có lỗi xảy ra!")
        error = detail.get("error")
    else:
        message = str(detail)
        error = None

    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(
            status_code=exc.status_code,
            message=message,
            data=None,
            error=error,
            path=str(request.url.path),
        ),
    )

# API 1: GET /flights - Lấy danh sách chuyến bay (có filter theo status)
@app.get("/flights")
async def get_flights(status: Optional[str] = None):
    if status:
        normalized = status.strip().lower()
        result = [f for f in flights_db if f["status"].lower() == normalized]
    else:
        result = flights_db

    return build_envelope(
        status_code=200,
        message="Lấy danh sách chuyến bay thành công!",
        data=result,
        error=None,
        path="/flights",
    )

# API 2: POST /flights - Tạo mới một chuyến bay
@app.post("/flights", status_code=status.HTTP_201_CREATED)
async def create_flight(payload: FlightCreateRequest):
    if find_flight_by_number(payload.flight_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Lỗi: Số hiệu chuyến bay này đã tồn tại trên hệ thống điều hành!",
                "error": "ERR-AIR-01: Flight number conflict in current active schedule database.",
            },
        )

    new_flight = {
        "id": get_next_id(),
        "flight_number": payload.flight_number,
        "destination": payload.destination,
        "available_seats": payload.available_seats,
        "status": "scheduled",
        "created_at": datetime.now().isoformat(),
    }
    flights_db.append(new_flight)

    return build_envelope(
        status_code=status.HTTP_201_CREATED,
        message="Khởi tạo chuyến bay mới thành công!",
        data=new_flight,
        error=None,
        path="/flights",
    )

# API 3: DELETE /flights/{flight_id} - Hủy bỏ / Xóa một chuyến bay
@app.delete("/flights/{flight_id}")
async def delete_flight(flight_id: int):
    flight = find_flight_by_id(flight_id)
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Lỗi: Không tìm thấy mã chuyến bay yêu cầu để hủy!",
                "error": "ERR-AIR-02: Target flight ID is missing from system scope.",
            },
        )

    flights_db.remove(flight)

    return build_envelope(
        status_code=200,
        message="Hủy chuyến bay thành công!",
        data=None,
        error=None,
        path=f"/flights/{flight_id}",
    )
