from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from . import config

config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
config.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# check_same_thread=False: FastAPI может обращаться к SQLite из разных потоков.
# Для нагрузки пилота (единицы одновременных запросов) этого достаточно.
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# WAL — чтобы параллельные чтение/запись (расчёт + генерация PDF одновременно
# у разных бригад) не блокировали друг друга наглухо.
with engine.connect() as conn:
    conn.exec_driver_sql("PRAGMA journal_mode=WAL;")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI-зависимость: сессия БД на время одного запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (регистрация моделей перед create_all)
    Base.metadata.create_all(bind=engine)
