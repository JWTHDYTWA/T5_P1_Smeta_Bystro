import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, pricing
from .database import SessionLocal, init_db
from .routers import auth, calculate, documents, history, materials

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("smetabystro")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if config.AUTO_SEED_ON_STARTUP:
        db = SessionLocal()
        try:
            n = pricing.seed_from_csv_if_empty(db)
            if n:
                logger.info("Автозагрузка базы цен: %s позиций из data/prices.csv", n)
        finally:
            db.close()

    yield

    logger.info("Остановка СметаБыстро")


app = FastAPI(title="СметаБыстро", version="0.1.0-mvp", lifespan=lifespan)

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
    Приводим ошибки Pydantic к формату: {"error": {"code": "VALIDATION_ERROR", "message": ...}}.
    Очищаем технические префиксы Pydantic v2 ("Value error, ").
    """
    first_error = exc.errors()[0] if exc.errors() else {}
    raw_message = first_error.get("msg", "Проверьте введённые данные")

    message = (
        raw_message.removeprefix("Value error, ")
        .removeprefix("Assertion failed, ")
        .strip()
    )

    return JSONResponse(
        status_code=400,
        content={"error": {"code": "VALIDATION_ERROR", "message": message}},
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Разворачиваем exc.detail, если там уже передан словарь ошибки {"error": ...},
    чтобы FastAPI не оборачивал его повторно в {"detail": {"error": ...}}.
    """
    if isinstance(exc.detail, dict):
        if "error" in exc.detail:
            content = exc.detail
        else:
            content = {"error": exc.detail}
    elif isinstance(exc.detail, str):
        code = "VALIDATION_ERROR" if exc.status_code == 400 else f"HTTP_{exc.status_code}"
        content = {
            "error": {
                "code": code,
                "message": exc.detail,
            }
        }
    else:
        content = {"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}}

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


app.include_router(auth.router)
app.include_router(materials.router)
app.include_router(calculate.router)
app.include_router(documents.router)
app.include_router(history.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=str(config.BASE_DIR.parent / "frontend"), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
