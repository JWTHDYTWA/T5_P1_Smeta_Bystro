"""
Core-3: Генерация сметы и КП в PDF.

Вход -> обработка -> выход (раздел 1.1):
  результат расчёта + данные подрядчика -> подстановка в HTML-шаблон,
  рендер в PDF -> два файла: внутренняя смета (с себестоимостью и маржой)
  и внешнее КП (без себестоимости, с логотипом).

ВАЖНО (приватность, раздел 1.1): себестоимость и маржа подставляются ТОЛЬКО
в internal-шаблон. client-шаблон их не получает вообще (не просто скрывает
CSS-ом) — так исключается случайная утечка в DOM/тексте клиентского PDF.
"""
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from . import config
from .models import User
from .schemas import CalculateRequest, CalculateResponse

_env = Environment(
    loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def generate_documents(
    calculation_id: int,
    user: User,
    req: CalculateRequest,
    result: CalculateResponse,
) -> tuple[str, str]:
    """Рендерит оба PDF, сохраняет на диск, возвращает пути к файлам."""
    internal_path = config.DOCUMENTS_DIR / f"{calculation_id}_internal.pdf"
    client_path = config.DOCUMENTS_DIR / f"{calculation_id}_client.pdf"

    common_ctx = {
        "brand_name": user.brand_name or "Бригада",
        "logo_path": user.logo_path,
        "calculation_id": calculation_id,
        "req": req,
        "result": result,
    }

    # Внутренняя смета — с себестоимостью и маржой
    internal_html = _env.get_template("estimate_internal.html").render(**common_ctx)
    HTML(string=internal_html, base_url=str(config.TEMPLATES_DIR)).write_pdf(str(internal_path))

    # Внешнее КП — без себестоимости, только итог для заказчика
    client_html = _env.get_template("estimate_client.html").render(**common_ctx)
    HTML(string=client_html, base_url=str(config.TEMPLATES_DIR)).write_pdf(str(client_path))

    return str(internal_path), str(client_path)
