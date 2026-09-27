import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, pricing
from .database import SessionLocal, init_db
from .routers import auth, calculate, documents, history, materials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smetabystro")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- код до yield выполняется один раз при старте (аналог on_event("startup")) ---
    init_db()
    if config.AUTO_SEED_ON_STARTUP:
        db = SessionLocal()
        try:
            n = pricing.seed_from_csv_if_empty(db)
            if n:
                logger.info("Автозагрузка базы цен: %s позиций из data/prices.csv", n)
        finally:
            db.close()

    yield  # --- приложение работает ---

    # --- код после yield выполняется один раз при остановке (аналог on_event("shutdown")) ---
    # Отдельно закрывать нечего: SessionLocal создаёт короткоживущие сессии
    # на каждый запрос (см. get_db в database.py), а не держит одно
    # долгоживущее соединение, которое нужно было бы явно закрывать здесь.
    logger.info("Остановка СметаБыстро")


app = FastAPI(title="СметаБыстро", version="0.1.0-mvp", lifespan=lifespan)

# ДЕМО: разрешаем всё. В реальной эксплуатации сузить до конкретного домена туннеля.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Приводим стандартные 422-ошибки Pydantic/FastAPI к единому формату ошибок
    из раздела 3.1 ТЗ: {"error": {"code": "VALIDATION_ERROR", "message": ...}}.
    """
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Проверьте введённые данные")
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "VALIDATION_ERROR", "message": message}},
    )


app.include_router(auth.router)
app.include_router(materials.router)
app.include_router(calculate.router)
app.include_router(documents.router)
app.include_router(history.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Раздача фронтенда (простые статические HTML/JS/CSS без фреймворка, раздел 2.1)
app.mount("/", StaticFiles(directory=str(config.BASE_DIR.parent / "frontend"), html=True), name="frontend")
