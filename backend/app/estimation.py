"""
Склеивает Core-1 (calculator) и Core-2 (pricing) в единый результат расчёта,
который затем и /api/calculate, и /api/documents/generate используют одинаково
(документы НЕ доверяют result_json от клиента и пересчитывают всё заново).
"""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from . import calculator, pricing
from .schemas import CalculateRequest, CalculateResponse, VolumeItem


def build_estimate(db: Session, req: CalculateRequest) -> CalculateResponse:
    calc = calculator.calculate_roof(
        slopes=req.slopes,
        eave_length_m=req.eave_length_m,
        ridge_length_m=req.ridge_length_m,
        abutments_count=req.abutments_count,
        material_sku=req.material_sku,
    )

    skus_needed = [line.sku for line in calc.lines if line.sku]
    prices = pricing.get_prices(db, req.region, req.supplier, skus_needed)

    volumes = []
    materials_cost = 0.0
    oldest_price_date: Optional[date] = None
    any_stale = False

    for line in calc.lines:
        price_row = prices[line.sku]
        line_sum = round(line.qty * price_row.price, 2)
        materials_cost += line_sum
        stale = pricing.is_stale(price_row.updated_at)
        any_stale = any_stale or stale
        if oldest_price_date is None or price_row.updated_at < oldest_price_date:
            oldest_price_date = price_row.updated_at

        volumes.append(VolumeItem(
            sku=line.sku,
            name=line.name,
            unit=line.unit,
            qty=line.qty,
            unit_price=price_row.price,
            sum=line_sum,
            price_is_stale=stale,
        ))

    materials_cost = round(materials_cost, 2)

    # Расчёт стоимости работ: расценка подрядчика x объём, соответствующий
    # единице измерения расценки. Это явное допущение (в примере ТЗ раздел 3.1
    # цифры work_cost не выводятся из входных данных однозначно) — здесь
    # выбрана прозрачная и предсказуемая формула, а не подгонка под пример.
    work_cost = 0.0
    for rate in req.work_rates:
        if rate.unit == "m2":
            qty = calc.total_area_m2
        elif rate.unit == "m":
            qty = req.eave_length_m + req.ridge_length_m
        else:  # "pcs" и всё прочее — расценка за проект целиком
            qty = 1
        work_cost += rate.price * qty
    work_cost = round(work_cost, 2)

    total_cost = round(materials_cost + work_cost, 2)

    return CalculateResponse(
        slopes_area_m2=calc.slopes_area_m2,
        total_area_m2=calc.total_area_m2,
        volumes=volumes,
        work_cost=work_cost,
        materials_cost=materials_cost,
        total_cost=total_cost,
        price_date=oldest_price_date,
        price_is_stale=any_stale,
    )
