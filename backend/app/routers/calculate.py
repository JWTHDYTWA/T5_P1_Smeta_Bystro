import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import calculator, config, estimation, pricing, security
from ..database import get_db
from ..models import User
from ..schemas import CalculateRequest, CalculateResponse

router = APIRouter(prefix="/api/calculate", tags=["calculate"])
logger = logging.getLogger("smetabystro")


@router.post("", response_model=CalculateResponse)
def calculate(
    payload: CalculateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(security.get_current_user),
):
    started = time.monotonic()
    try:
        result = estimation.build_estimate(db, payload)
    except calculator.CalculatorError as exc:
        raise HTTPException(status_code=400, detail={
            "error": {"code": "VALIDATION_ERROR", "message": str(exc)}
        })
    except pricing.PriceLookupError as exc:
        raise HTTPException(status_code=404, detail={
            "error": {"code": "PRICE_NOT_FOUND", "message": "Этот материал пока не в базе, выберите другой"}
        }) from exc

    elapsed = time.monotonic() - started
    if elapsed > config.CALCULATE_TIMEOUT_SECONDS:
        # Критерий приёмки (раздел 1.1): расчёт должен укладываться в 3 сек.
        # Не блокируем ответ, но фиксируем нарушение для последующей проверки.
        logger.warning("Расчёт превысил целевые 3 секунды: %.2fs", elapsed)

    return result
