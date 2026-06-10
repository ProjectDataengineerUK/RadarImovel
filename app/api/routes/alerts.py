from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.middleware.auth import get_current_user
from app.models.user import User, Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Alert).filter_by(user_id=current_user.id)
    total = q.count()
    items = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": items}
