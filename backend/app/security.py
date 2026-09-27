"""
!!! ВНИМАНИЕ: это НЕ настоящая аутентификация !!!

Согласно разделу 1.1 ТЗ, на пилоте вход выполняется по номеру телефона БЕЗ
кода подтверждения (SMS-провайдер сознательно исключён из MVP). Это значит:
любой, кто знает номер телефона бригадира, может зайти под его аккаунтом.
Риск принят для пилота на 5–10 лично известных бригад (см. раздел 1.1
"Жёсткая верификация MVP" и критику приватности данных).

Сессия — это просто подписанный (не зашифрованный!) идентификатор
пользователя в cookie. Он защищает только от подделки cookie посторонним,
но не от входа по чужому номеру. Для продакшена это нужно заменить на
полноценную аутентификацию.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import User

_serializer = URLSafeTimedSerializer(config.SESSION_SECRET, salt="smetabystro-session")


def create_session_cookie_value(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def _decode_session_cookie(value: str) -> int | None:
    try:
        data = _serializer.loads(value, max_age=config.SESSION_MAX_AGE_SECONDS)
        return int(data["user_id"])
    except (BadSignature, SignatureExpired, KeyError, ValueError, TypeError):
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Зависимость FastAPI: достаёт текущего пользователя из cookie сессии."""
    raw = request.cookies.get(config.SESSION_COOKIE_NAME)
    user_id = _decode_session_cookie(raw) if raw else None

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Войдите заново по номеру телефона"}},
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Войдите заново по номеру телефона"}},
        )
    return user
