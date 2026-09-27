"""
Пути и константы приложения.
Всё, что раньше было бы "магическими числами" в коде, вынесено сюда или
в config/roof_norms.json — см. раздел 3.2 ТЗ.
"""
from pathlib import Path

# Корень бэкенда (папка backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STORAGE_DIR = BASE_DIR / "storage"
DOCUMENTS_DIR = STORAGE_DIR / "documents"
DB_PATH = STORAGE_DIR / "db.sqlite3"

ROOF_NORMS_PATH = CONFIG_DIR / "roof_norms.json"
PRICES_CSV_PATH = DATA_DIR / "prices.csv"

DATABASE_URL = f"sqlite:///{DB_PATH}"

# ДЕМО-СЕКРЕТ. В реальном проекте — переменная окружения, не значение в коде.
SESSION_SECRET = "smetabystro-demo-secret-change-me"
SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 дней — сессия бригадира на объекте

# Критерии приёмки из раздела 1.1 ТЗ
CALCULATE_TIMEOUT_SECONDS = 3
DOCUMENTS_TIMEOUT_SECONDS = 10
PRICE_STALE_AFTER_DAYS = 10

# Если в БД нет ни одной цены при старте — автоматически подхватить data/prices.csv.
# Удобно для демонстрации; в реальной эксплуатации импорт делает оператор вручную
# через scripts/import_prices.py (см. раздел 3.2 ТЗ).
AUTO_SEED_ON_STARTUP = True
