import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_role
from app.calculator.engine import _load_seed_costs
from app.core.database import get_db
from app.entitlements.audit import audit
from app.models.cost_table import CostTable
from app.models.user import User

router = APIRouter(prefix="/admin/costs", tags=["admin"])


class CostTableIn(BaseModel):
    state: str = Field(..., min_length=2, max_length=2)
    itbi_pct: float = Field(..., ge=0, le=10)
    registro_pct: float = Field(..., ge=0, le=5)
    escritura_pct: float = Field(..., ge=0, le=5)


class CostTableOut(BaseModel):
    id: str
    state: str
    itbi_pct: float
    registro_pct: float
    escritura_pct: float
    active: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CostTableOut])
def list_costs(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("operador")),
):
    rows = db.query(CostTable).order_by(CostTable.state).all()
    # Se vazio, retorna seeds como referência
    if not rows:
        seeds = _load_seed_costs()
        return [
            CostTableOut(
                id=s,
                state=s,
                itbi_pct=v["itbi_pct"],
                registro_pct=v["registro_pct"],
                escritura_pct=v["escritura_pct"],
                active=True,
                updated_at=datetime.now(timezone.utc),
            )
            for s, v in seeds.get("states", {}).items()
        ]
    return rows


@router.put("/{state}")
def upsert_cost(
    state: str,
    body: CostTableIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    state = state.upper()
    row = db.query(CostTable).filter_by(state=state).first()
    before = None
    if row:
        before = {
            "itbi_pct": float(row.itbi_pct),
            "registro_pct": float(row.registro_pct),
            "escritura_pct": float(row.escritura_pct),
        }
        row.itbi_pct = body.itbi_pct
        row.registro_pct = body.registro_pct
        row.escritura_pct = body.escritura_pct
        row.updated_by = user.id
        action = "cost.update"
    else:
        row = CostTable(
            state=state,
            itbi_pct=body.itbi_pct,
            registro_pct=body.registro_pct,
            escritura_pct=body.escritura_pct,
            updated_by=user.id,
        )
        db.add(row)
        action = "cost.create"

    db.flush()
    after = {
        "itbi_pct": float(row.itbi_pct),
        "registro_pct": float(row.registro_pct),
        "escritura_pct": float(row.escritura_pct),
    }
    audit(db, actor=user, action=action, entity_type="cost_table", entity_id=state, before=before, after=after)

    _load_seed_costs.cache_clear()

    return {"state": state, "itbi_pct": float(row.itbi_pct), "registro_pct": float(row.registro_pct), "escritura_pct": float(row.escritura_pct)}
