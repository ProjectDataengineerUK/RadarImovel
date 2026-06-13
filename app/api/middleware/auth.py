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

ROLE_ORDER = {"user": 0, "suporte": 1, "operador": 2, "admin": 3}

_FIREBASE_PROJECT_ID = "radarimovel-18a25"


def _ensure_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    settings = get_settings()
    cred_dict = json.loads(settings.firebase_credentials_json)
    private_key = cred_dict.get("private_key", "")
    if private_key.startswith("-----BEGIN"):
        # Real service account certificate
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        # Placeholder or missing key: use Application Default Credentials (Cloud Run SA)
        # Token verification only needs the project ID — no SA key required.
        firebase_admin.initialize_app(options={"projectId": _FIREBASE_PROJECT_ID})
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
        # Auto-register on first login
        email = decoded.get("email", f"{firebase_uid}@unknown.local")
        is_first_user = db.query(User).count() == 0
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            role="admin" if is_first_user else "user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def get_current_user_or_none(
    token=Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user(token=token, db=db)
    except HTTPException:
        return None


def require_role(min_role: str):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_ORDER.get(user.role, 0) < ROLE_ORDER.get(min_role, 0):
            raise HTTPException(403, detail={"code": "FORBIDDEN_ROLE", "required": min_role})
        return user
    return dep


def require_feature(flag: str):
    async def dep(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        from app.entitlements.service import has_feature
        if not has_feature(db, user, flag):
            raise HTTPException(403, detail={"code": "PLAN_LIMIT", "feature": flag})
        return user
    return dep


def consume_quota(feature: str, period: str = "day"):
    async def dep(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        from app.entitlements.service import consume
        if not consume(db, user, feature, period):
            raise HTTPException(429, detail={"code": "QUOTA_EXCEEDED", "feature": feature})
        return user
    return dep
