"""
Core-1: Калькулятор объёмов кровли.

Вход -> обработка -> выход, как описано в разделе 1.1 и формулы из раздела 3.2:
  площадь ската = (длина x ширина) / cos(угол наклона)
  итоговая площадь = площадь x (1 + коэффициент нахлёста)
  количество листов = округление вверх (итоговая площадь / площадь листа)
  обрешётка / крепёж / водосток — по нормативам на единицу площади/периметра.

ВАЖНО (зафиксированное допущение, требует проверки с кровельщиком на дне 2):
длина/ширина ската в этой реализации трактуются как ГОРИЗОНТАЛЬНАЯ ПРОЕКЦИЯ
(план сверху), поэтому формула площадь/cos(угол) корректно даёт площадь по
уклону. Если бригадир на практике измеряет длину рулеткой ПО САМОМУ СКАТУ,
этот шаг делить на cos() не нужно — иначе площадь будет завышена (при 25° —
примерно на 10%, при 45° — почти на 40%), и тест "расхождение с ручным
расчётом не более 5%" (раздел 1.1) не пройдёт. Это ровно то расхождение,
которое нужно закрыть в день 2 на трёх реальных объектах.
"""
import json
import math
from dataclasses import dataclass, field
from typing import List, Optional

from . import config


@dataclass
class VolumeLine:
    sku: Optional[str]
    name: str
    unit: str
    qty: float


@dataclass
class CalculationResult:
    slopes_area_m2: List[float]
    total_area_m2: float
    lines: List[VolumeLine] = field(default_factory=list)


class CalculatorError(Exception):
    """Ошибка нормативов/входных данных, которую роутер превращает в 400."""


_norms_cache: Optional[dict] = None


def load_norms() -> dict:
    global _norms_cache
    if _norms_cache is None:
        with open(config.ROOF_NORMS_PATH, "r", encoding="utf-8") as f:
            _norms_cache = json.load(f)
    return _norms_cache


def _overlap_coefficient(angle_deg: float, norms: dict) -> float:
    overlap = norms["overlap"]
    if angle_deg < overlap["angle_threshold_deg"]:
        return overlap["coefficient_low_angle"]
    return overlap["coefficient_high_angle"]


def calculate_roof(
    slopes: list,               # list[SlopeIn]-like объектов с length_m/width_m/angle_deg
    eave_length_m: float,
    ridge_length_m: float,
    abutments_count: int,
    material_sku: str,
) -> CalculationResult:
    norms = load_norms()

    material = norms["materials"].get(material_sku)
    if material is None:
        raise CalculatorError(f"Материал с артикулом '{material_sku}' не найден в нормативах")

    slopes_area: List[float] = []
    total_area = 0.0

    for slope in slopes:
        angle_rad = math.radians(slope.angle_deg)
        raw_area = (slope.length_m * slope.width_m) / math.cos(angle_rad)
        coeff = _overlap_coefficient(slope.angle_deg, norms)
        final_area = raw_area * coeff
        slopes_area.append(round(final_area, 2))
        total_area += final_area

    total_area = round(total_area, 2)

    lines: List[VolumeLine] = []

    # Основной материал (листы)
    sheets_qty = math.ceil(total_area / material["sheet_area_m2"])
    lines.append(VolumeLine(sku=material_sku, name=material["name"], unit=material["unit"], qty=sheets_qty))

    # Обрешётка — считается всегда, отдельный SKU в запросе не требуется
    battens = norms["battens"]
    battens_qty = round(total_area * battens["rate_per_m2"], 1)
    lines.append(VolumeLine(sku=battens["sku"], name=battens["name"], unit=battens["unit"], qty=battens_qty))

    # Крепёж
    fasteners = norms["fasteners"]
    fasteners_qty = math.ceil(total_area * fasteners["rate_per_m2"])
    lines.append(VolumeLine(sku=fasteners["sku"], name=fasteners["name"], unit=fasteners["unit"], qty=fasteners_qty))

    # Водосток — по длине карниза
    gutter = norms["gutter"]
    gutter_qty = round(eave_length_m * gutter["rate_per_eave_m"], 1)
    if gutter_qty > 0:
        lines.append(VolumeLine(sku=gutter["sku"], name=gutter["name"], unit=gutter["unit"], qty=gutter_qty))

    # Планки примыкания — по числу примыканий
    if abutments_count > 0:
        abutment = norms["abutment_strip"]
        abutment_qty = round(abutments_count * abutment["rate_per_abutment"], 1)
        lines.append(VolumeLine(sku=abutment["sku"], name=abutment["name"], unit=abutment["unit"], qty=abutment_qty))

    return CalculationResult(slopes_area_m2=slopes_area, total_area_m2=total_area, lines=lines)
