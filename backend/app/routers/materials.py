import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import pricing, security, calculator
from ..database import get_db
from ..models import User
from ..schemas import MaterialOut

logger = logging.getLogger("smetabystro")

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=List[MaterialOut])
def list_materials(
    region: str,
    supplier: str,
    db: Session = Depends(get_db),
    _user: User = Depends(security.get_current_user),
):
    rows = pricing.list_materials(db, region, supplier)
    norms = calculator.load_norms()
    allowed = set(norms.get("materials", {}).keys())
    filtered = [r for r in rows if r.sku in allowed]
    logger.debug("Returning %d materials (filtered to norms): %s", len(filtered), ", ".join([r.sku for r in filtered]))
    return [
        MaterialOut(
            sku=row.sku,
            name=row.name,
            unit=row.unit,
            price=row.price,
            updated_at=row.updated_at,
            is_stale=pricing.is_stale(row.updated_at),
        )
        for row in filtered
    ]
