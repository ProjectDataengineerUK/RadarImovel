"""Admin: fila de possíveis duplicatas — listar, mesclar ou descartar."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user, require_role
from app.core.database import get_db
from app.entitlements.audit import audit
from app.models.property import Property
from app.models.user import User

router = APIRouter(prefix="/admin/dedup", tags=["admin"])


class DuplicateItem(BaseModel):
    id: str
    title: str | None
    city: str
    state: str
    current_value: float
    official_url: str
    possible_duplicate_of: str
    first_seen_at: datetime

    model_config = {"from_attributes": True}


class MergeRequest(BaseModel):
    keep_id: str
    discard_id: str


@router.get("", response_model=list[DuplicateItem])
def list_duplicates(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("operador")),
):
    """Lista imóveis marcados como possíveis duplicatas pendentes de revisão."""
    rows = (
        db.query(Property)
        .filter(Property.possible_duplicate_of.isnot(None))
        .order_by(Property.first_seen_at.desc())
        .limit(200)
        .all()
    )
    return [
        DuplicateItem(
            id=str(r.id),
            title=r.title,
            city=r.city,
            state=r.state,
            current_value=float(r.current_value),
            official_url=r.official_url,
            possible_duplicate_of=str(r.possible_duplicate_of),
            first_seen_at=r.first_seen_at,
        )
        for r in rows
    ]


@router.post("/merge")
def merge(
    body: MergeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("operador")),
):
    """Confirma mesclagem: mantém keep_id, desativa discard_id."""
    keep = db.get(Property, uuid.UUID(body.keep_id))
    discard = db.get(Property, uuid.UUID(body.discard_id))
    if not keep or not discard:
        raise HTTPException(404, detail="Imóvel não encontrado")

    # Reatribui offers do descartado para o mantido
    for offer in discard.offers:
        offer.property_id = keep.id

    discard.status = "merged"
    discard.possible_duplicate_of = None

    audit(
        db,
        actor=user,
        action="dedup.merge",
        entity_type="property",
        entity_id=str(keep.id),
        before={"merged_from": str(discard.id)},
        after={"status": "merged"},
    )

    db.commit()
    return {"kept": str(keep.id), "discarded": str(discard.id)}


@router.delete("/{property_id}/flag")
def dismiss(
    property_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("operador")),
):
    """Descarta o flag de duplicata (falso positivo)."""
    prop = db.get(Property, uuid.UUID(property_id))
    if not prop:
        raise HTTPException(404)
    if prop.possible_duplicate_of is None:
        raise HTTPException(400, detail="Imóvel não está na fila de duplicatas")

    before = str(prop.possible_duplicate_of)
    prop.possible_duplicate_of = None

    audit(
        db,
        actor=user,
        action="dedup.dismiss",
        entity_type="property",
        entity_id=property_id,
        before={"possible_duplicate_of": before},
        after={"possible_duplicate_of": None},
    )

    db.commit()
    return {"property_id": property_id, "flag_cleared": True}
