import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import security
from ..database import get_db
from ..models import Calculation, User
from ..schemas import CalculateRequest, CalculateResponse, HistoryDetailOut, HistoryItemOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=List[HistoryItemOut])
def list_history(db: Session = Depends(get_db), user: User = Depends(security.get_current_user)):
    rows = (
        db.query(Calculation)
        .filter(Calculation.user_id == user.id)
        .order_by(Calculation.created_at.desc())
        .all()
    )
    out = []
    for row in rows:
        result = json.loads(row.result_json)
        req = json.loads(row.input_json)
        material_name = next((v["name"] for v in result["volumes"] if v.get("sku") == req.get("material_sku")), "—")
        out.append(HistoryItemOut(
            id=row.id,
            created_at=row.created_at,
            total_cost=result["total_cost"],
            material_name=material_name,
            has_documents=bool(row.internal_pdf_path and row.client_pdf_path),
        ))
    return out


@router.get("/{calc_id}", response_model=HistoryDetailOut)
def get_history_item(calc_id: int, db: Session = Depends(get_db), user: User = Depends(security.get_current_user)):
    row = db.get(Calculation, calc_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail={
            "error": {"code": "PRICE_NOT_FOUND", "message": "Расчёт не найден"}
        })

    return HistoryDetailOut(
        id=row.id,
        created_at=row.created_at,
        input=CalculateRequest.model_validate_json(row.input_json),
        result=CalculateResponse.model_validate_json(row.result_json),
        internal_pdf_url=f"/api/documents/{row.id}/internal" if row.internal_pdf_path else None,
        client_pdf_url=f"/api/documents/{row.id}/client" if row.client_pdf_path else None,
    )
