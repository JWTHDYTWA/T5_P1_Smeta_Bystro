import json
import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import calculator, config, estimation, pdf_generator, pricing, security
from ..database import get_db
from ..models import Calculation, User
from ..schemas import DocumentsGenerateRequest, DocumentsGenerateResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger("smetabystro")


@router.post("/generate", response_model=DocumentsGenerateResponse)
def generate_documents(
    payload: DocumentsGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(security.get_current_user),
):
    """
    Пересчитывает смету на сервере (не доверяя клиенту), сохраняет расчёт в
    историю (шаг 8 Data Flow, раздел 2.2) и рендерит два PDF (шаг 6).
    """
    started = time.monotonic()
    req = payload.calculate_request

    try:
        result = estimation.build_estimate(db, req)
    except calculator.CalculatorError as exc:
        raise HTTPException(status_code=400, detail={
            "error": {"code": "VALIDATION_ERROR", "message": str(exc)}
        })
    except pricing.PriceLookupError as exc:
        raise HTTPException(status_code=404, detail={
            "error": {"code": "PRICE_NOT_FOUND", "message": "Этот материал пока не в базе, выберите другой"}
        }) from exc

    calc_row = Calculation(
        user_id=user.id,
        input_json=req.model_dump_json(),
        result_json=result.model_dump_json(),
    )
    db.add(calc_row)
    db.commit()
    db.refresh(calc_row)

    try:
        internal_path, client_path = pdf_generator.generate_documents(calc_row.id, user, req, result)
    except Exception as exc:  # рендер PDF — единственное место, где чаще всего падает WeasyPrint
        logger.exception("Ошибка генерации PDF для расчёта %s", calc_row.id)
        raise HTTPException(status_code=500, detail={
            "error": {"code": "PDF_GENERATION_FAILED", "message": "Не удалось сформировать документ, попробуйте ещё раз"}
        }) from exc

    calc_row.internal_pdf_path = internal_path
    calc_row.client_pdf_path = client_path
    db.commit()

    elapsed = time.monotonic() - started
    if elapsed > config.DOCUMENTS_TIMEOUT_SECONDS:
        logger.warning("Генерация документов превысила целевые 10 секунд: %.2fs", elapsed)

    return DocumentsGenerateResponse(
        calculation_id=calc_row.id,
        internal_pdf_url=f"/api/documents/{calc_row.id}/internal",
        client_pdf_url=f"/api/documents/{calc_row.id}/client",
        result=result,
    )


def _get_owned_calculation(db: Session, calc_id: int, user: User) -> Calculation:
    calc_row = db.get(Calculation, calc_id)
    if calc_row is None or calc_row.user_id != user.id:
        # Не различаем "не найдено" и "чужое" в ответе — не палим существование чужих ID
        raise HTTPException(status_code=404, detail={
            "error": {"code": "PRICE_NOT_FOUND", "message": "Расчёт не найден"}
        })
    return calc_row


@router.get("/{calc_id}/internal")
def download_internal(calc_id: int, db: Session = Depends(get_db), user: User = Depends(security.get_current_user)):
    calc_row = _get_owned_calculation(db, calc_id, user)
    if not calc_row.internal_pdf_path:
        raise HTTPException(status_code=404, detail={"error": {"code": "PRICE_NOT_FOUND", "message": "Документ ещё не сформирован"}})
    return FileResponse(calc_row.internal_pdf_path, media_type="application/pdf", filename=f"smeta_{calc_id}.pdf")


@router.get("/{calc_id}/client")
def download_client(calc_id: int, db: Session = Depends(get_db), user: User = Depends(security.get_current_user)):
    calc_row = _get_owned_calculation(db, calc_id, user)
    if not calc_row.client_pdf_path:
        raise HTTPException(status_code=404, detail={"error": {"code": "PRICE_NOT_FOUND", "message": "Документ ещё не сформирован"}})
    return FileResponse(calc_row.client_pdf_path, media_type="application/pdf", filename=f"kp_{calc_id}.pdf")
