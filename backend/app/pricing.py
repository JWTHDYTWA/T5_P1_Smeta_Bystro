"""
Core-2: База цен материалов по региону.

Вход -> обработка -> выход (раздел 1.1):
  регион, поставщик, список позиций -> выборка из локальной базы,
  проверка даты обновления -> цена за единицу + предупреждение о "старой" цене.
"""
import csv
from datetime import date, datetime
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from . import config
from .models import MaterialPrice


class PriceLookupError(Exception):
    """Материал не найден в базе цен региона/поставщика — соответствует PRICE_NOT_FOUND."""


def is_stale(updated_at: date) -> bool:
    return (date.today() - updated_at).days > config.PRICE_STALE_AFTER_DAYS


def get_prices(db: Session, region: str, supplier: str, skus: Iterable[str]) -> Dict[str, MaterialPrice]:
    """
    Возвращает {sku: MaterialPrice} для всех запрошенных артикулов.
    Бросает PriceLookupError, если хотя бы один артикул не найден
    (в реальном UI это должно предотвращаться выбором из /api/materials,
    здесь — дополнительная защита на бэкенде).
    """
    skus = list(skus)
    rows = (
        db.query(MaterialPrice)
        .filter(
            MaterialPrice.region == region,
            MaterialPrice.supplier == supplier,
            MaterialPrice.sku.in_(skus),
        )
        .all()
    )
    found = {row.sku: row for row in rows}
    missing = set(skus) - set(found.keys())
    if missing:
        raise PriceLookupError(f"Материалы не найдены в базе региона '{region}'/'{supplier}': {', '.join(sorted(missing))}")
    return found


def list_materials(db: Session, region: str, supplier: str):
    return (
        db.query(MaterialPrice)
        .filter(MaterialPrice.region == region, MaterialPrice.supplier == supplier)
        .order_by(MaterialPrice.name)
        .all()
    )


def seed_from_csv_if_empty(db: Session, csv_path=None) -> int:
    """
    Импорт data/prices.csv в таблицу MaterialPrice, если она пуста.
    Дублирует логику scripts/import_prices.py для удобства демо-запуска
    (см. AUTO_SEED_ON_STARTUP в app/config.py). В реальной эксплуатации
    обновление цен — ручной запуск scripts/import_prices.py оператором
    (раздел 3.2 ТЗ).
    """
    if db.query(MaterialPrice).first() is not None:
        return 0

    csv_path = csv_path or config.PRICES_CSV_PATH
    return import_prices_csv(db, csv_path)


def import_prices_csv(db: Session, csv_path) -> int:
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing = (
                db.query(MaterialPrice)
                .filter_by(region=row["region"], supplier=row["supplier"], sku=row["sku"])
                .first()
            )
            updated_at = datetime.strptime(row["updated_at"].strip(), "%Y-%m-%d").date()
            if existing:
                existing.name = row["name"]
                existing.unit = row["unit"]
                existing.price = float(row["price"])
                existing.updated_at = updated_at
            else:
                db.add(MaterialPrice(
                    region=row["region"],
                    supplier=row["supplier"],
                    sku=row["sku"],
                    name=row["name"],
                    unit=row["unit"],
                    price=float(row["price"]),
                    updated_at=updated_at,
                ))
            count += 1
    db.commit()
    return count
