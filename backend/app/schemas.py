from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------- Аутентификация (ДЕМО) ----------

class LoginRequest(BaseModel):
    phone: str = Field(..., description="Формат +7XXXXXXXXXX")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        digits_ok = v.startswith("+7") and v[1:].isdigit() and len(v) == 12
        if not digits_ok:
            raise ValueError("Номер телефона должен быть в формате +7XXXXXXXXXX")
        return v


class UserOut(BaseModel):
    id: int
    phone: str
    brand_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Материалы ----------

class MaterialOut(BaseModel):
    sku: str
    name: str
    unit: str
    price: float
    updated_at: date
    is_stale: bool


# ---------- Расчёт (Core-1) ----------

class SlopeIn(BaseModel):
    length_m: float
    width_m: float
    angle_deg: float

    @field_validator("length_m", "width_m")
    @classmethod
    def positive_length(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Длина ската должна быть больше 0")
        return v

    @field_validator("angle_deg")
    @classmethod
    def valid_angle(cls, v: float) -> float:
        if not (0 <= v <= 60):
            raise ValueError("Угол ската должен быть от 0 до 60°")
        return v


class WorkRateIn(BaseModel):
    name: str
    unit: str  # "m2" | "m" | "pcs"
    price: float


class CalculateRequest(BaseModel):
    roof_type: str = "pitched"
    slopes: List[SlopeIn]
    eave_length_m: float = Field(ge=0)
    ridge_length_m: float = Field(ge=0)
    abutments_count: int = Field(ge=0)
    material_sku: str
    accessories_sku: List[str] = []
    region: str
    supplier: str
    work_rates: List[WorkRateIn] = []


class VolumeItem(BaseModel):
    sku: Optional[str]
    name: str
    unit: str
    qty: float
    unit_price: Optional[float] = None
    sum: Optional[float] = None
    price_is_stale: bool = False


class CalculateResponse(BaseModel):
    slopes_area_m2: List[float]
    total_area_m2: float
    volumes: List[VolumeItem]
    work_cost: float
    materials_cost: float
    total_cost: float
    price_date: Optional[date]
    price_is_stale: bool


# ---------- Документы (Core-3) ----------

class DocumentsGenerateRequest(BaseModel):
    """
    Клиент присылает те же данные, что и в /api/calculate, плюс расценки
    на работы. Сервер пересчитывает всё заново сам (не доверяет result_json
    от клиента) и лишь после этого рендерит PDF и сохраняет историю.
    """
    calculate_request: CalculateRequest


class DocumentsGenerateResponse(BaseModel):
    calculation_id: int
    internal_pdf_url: str
    client_pdf_url: str
    result: CalculateResponse


# ---------- История ----------

class HistoryItemOut(BaseModel):
    id: int
    created_at: datetime
    total_cost: float
    material_name: str
    has_documents: bool


class HistoryDetailOut(BaseModel):
    id: int
    created_at: datetime
    input: CalculateRequest
    result: CalculateResponse
    internal_pdf_url: Optional[str]
    client_pdf_url: Optional[str]


# ---------- Ошибки (единый формат, раздел 3.1) ----------

class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
