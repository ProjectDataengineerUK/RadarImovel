import uuid
import json
import redis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.api.middleware.auth import get_current_user
from app.entitlements.service import get_entitlements
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


def _redis_client():
    return redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ent = get_entitlements(db, current_user)
    return {
        "id": str(current_user.id),
        "firebase_uid": current_user.firebase_uid,
        "role": current_user.role,
        "telegram_connected": current_user.telegram_chat_id is not None,
        "created_at": current_user.created_at,
        "plan": {
            "code": ent.plan_code,
            "features": ent.features,
            "limits": ent.limits,
        },
    }


@router.post("/telegram/token")
def generate_telegram_token(
    current_user: User = Depends(get_current_user),
):
    token = uuid.uuid4().hex[:8].upper()
    r = _redis_client()
    r.setex(
        f"tg_token:{token}",
        settings.telegram_token_ttl_seconds,
        str(current_user.id),
    )
    return {
        "token": token,
        "ttl_seconds": settings.telegram_token_ttl_seconds,
        "instructions": f"Envie /start {token} para o bot @RadarImovelBot no Telegram",
    }


@router.post("/telegram/connect")
async def connect_telegram_from_bot(
    payload: dict,
    db: Session = Depends(get_db),
):
    """Webhook interno chamado pelo bot Telegram quando recebe /start TOKEN."""
    token = payload.get("token", "").upper()
    chat_id = payload.get("chat_id")

    if not token or not chat_id:
        raise HTTPException(status_code=400, detail="token e chat_id são obrigatórios")

    r = _redis_client()
    user_id = r.get(f"tg_token:{token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.telegram_chat_id = int(chat_id)
    db.commit()
    r.delete(f"tg_token:{token}")
    return {"ok": True}
