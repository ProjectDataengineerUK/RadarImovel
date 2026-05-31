import json
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session

security = HTTPBearer()
_firebase_initialized = False


def _ensure_firebase():
    global _firebase_initialized
    if not _firebase_initialized:
        settings = get_settings()
        cred_dict = json.loads(settings.firebase_credentials_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True


async def get_current_user(
    token=Depends(security),
    db: Session = Depends(get_db),
) -> User:
    _ensure_firebase()
    try:
        decoded = firebase_auth.verify_id_token(token.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    firebase_uid = decoded["uid"]
    user = db.query(User).filter_by(firebase_uid=firebase_uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_or_none(
    token=Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user(token=token, db=db)
    except HTTPException:
        return None
