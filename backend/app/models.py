"""
Модель данных — см. раздел 2.3 ТЗ.
input_json / result_json хранятся как единый JSON-документ (сознательное
упрощение ради срока в неделю, см. раздел 2.3 "Правила целостности данных").
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    brand_name = Column(String(200), nullable=True)
    logo_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    work_rates = relationship("WorkRate", back_populates="user", cascade="all, delete-orphan")
    calculations = relationship("Calculation", back_populates="user", cascade="all, delete-orphan")


class WorkRate(Base):
    __tablename__ = "work_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    unit = Column(String(20), nullable=False)  # m2, m, pcs
    price = Column(Float, nullable=False)

    user = relationship("User", back_populates="work_rates")


class MaterialPrice(Base):
    __tablename__ = "material_prices"
    __table_args__ = (
        UniqueConstraint("region", "supplier", "sku", name="uq_region_supplier_sku"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    region = Column(String(50), nullable=False)
    supplier = Column(String(50), nullable=False)
    sku = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    unit = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    updated_at = Column(Date, nullable=False)


class Calculation(Base):
    __tablename__ = "calculations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_json = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Пути к сгенерированным PDF (заполняются после /api/documents/generate,
    # изначально пусты — расчёт можно сохранить и без документов).
    internal_pdf_path = Column(String(500), nullable=True)
    client_pdf_path = Column(String(500), nullable=True)

    user = relationship("User", back_populates="calculations")
