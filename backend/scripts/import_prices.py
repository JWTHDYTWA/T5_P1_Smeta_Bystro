#!/usr/bin/env python3
"""
Импорт data/prices.csv в таблицу material_prices.

Запускает оператор базы цен при каждом обновлении файла (раздел 3.2 ТЗ,
"Зафиксированные конфигурации"). Пример запуска из папки backend/:

    uv run scripts/import_prices.py
    uv run scripts/import_prices.py --csv data/prices_2026-10-01.csv
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.database import SessionLocal, init_db
from app.pricing import import_prices_csv


def main():
    parser = argparse.ArgumentParser(description="Импорт цен материалов в SQLite")
    parser.add_argument("--csv", default=str(config.PRICES_CSV_PATH), help="Путь к CSV-файлу с ценами")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        count = import_prices_csv(db, args.csv)
        print(f"Импортировано/обновлено позиций: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
