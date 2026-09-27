from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from .. import config, security
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    ДЕМО-вход: находим пользователя по номеру телефона или создаём нового.
    Кода подтверждения нет (см. app/security.py и раздел 1.1 ТЗ).
    """
    user = db.query(User).filter(User.phone == payload.phone).first()
    if user is None:
        user = User(phone=payload.phone)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = security.create_session_cookie_value(user.id)
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        max_age=config.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(config.SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(security.get_current_user)):
    return user
