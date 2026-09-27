# СметаБыстро — MVP
#
# Один контейнер = весь монолит (FastAPI + SQLite + WeasyPrint + статика фронтенда),
# в соответствии с разделом 2.1 ТЗ ("единый монолитный процесс").
#
# Зачем вообще Docker на локальном ПК, а не просто venv — см. раздел 2.1 ТЗ:
# WeasyPrint зависит от нативной библиотеки Pango, которую сложно
# ставить на "голом" Windows. Контейнер убирает эту разницу окружений.
#
# Зависимости ставятся через uv (быстрее pip, версии зафиксированы в uv.lock
# с хешами — воспроизводимая сборка, а не "что pip резолвнёт сегодня").

FROM python:3.12-slim

# Системные библиотеки, нужные WeasyPrint для рендера HTML -> PDF.
# С версии 53 WeasyPrint больше не использует Cairo (PDF рендерится через
# pydyf), поэтому libcairo2 здесь не нужен — только Pango и его зависимости.
# libglib2.0-0 указан явно: без него типична ошибка
# "cannot load library 'libgobject-2.0-0'" в минимальных образах вроде slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libglib2.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Официальный образ uv: копируем сам бинарник, ничего больше из него не нужно
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /usr/local/bin/

WORKDIR /app/backend

# Сначала только манифесты — отдельный кэшируемый слой, пока pyproject.toml/
# uv.lock не меняются, переустановки зависимостей при правках кода не будет
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

# Теперь код приложения
COPY backend/app ./app
COPY backend/config ./config
COPY backend/data ./data
COPY backend/templates ./templates
COPY backend/scripts ./scripts
COPY frontend /app/frontend

# storage/ — том для db.sqlite3 и сгенерированных PDF, должен переживать
# пересборку контейнера (см. раздел 2.1 ТЗ про резервное копирование)
RUN mkdir -p storage/documents
VOLUME ["/app/backend/storage"]

# uv кладёт venv в .venv рядом с pyproject.toml — используем его напрямую,
# без активации, через прямой путь к интерпретатору
ENV PATH="/app/backend/.venv/bin:$PATH"

EXPOSE 8000

# Без --reload: это для разработки, в контейнере он не нужен
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
