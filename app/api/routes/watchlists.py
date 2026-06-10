from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.middleware.auth import get_current_user
from app.models.user import User, Watchlist

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


class WatchlistCreate(BaseModel):
    state: str | None = None
    city: str | None = None
    max_price: Decimal | None = None
    min_discount: Decimal | None = None
    property_type: str | None = None
    bank_id: str | None = None


@router.get("")
def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Watchlist).filter_by(user_id=current_user.id, active=True).all()


@router.post("")
def create_watchlist(
    payload: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = Watchlist(user_id=current_user.id, **payload.model_dump())
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return wl


@router.put("/{watchlist_id}")
def update_watchlist(
    watchlist_id: str,
    payload: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter_by(id=watchlist_id, user_id=current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(wl, k, v)
    db.commit()
    db.refresh(wl)
    return wl


@router.delete("/{watchlist_id}")
def delete_watchlist(
    watchlist_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter_by(id=watchlist_id, user_id=current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    wl.active = False
    db.commit()
    return {"ok": True}
