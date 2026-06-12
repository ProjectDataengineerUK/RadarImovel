"""Curva preditiva de desconto — AT-008.

Calcula P(queda de preço em 30/60/90 dias) por imóvel combinando:
  (a) priors documentados em priors.yaml (tabela de transição por banco/modalidade)
  (b) estatística empírica de property_changes agrupada por banco+modalidade

Blending: weight = min(N_empírico / BOOTSTRAP_N, 1.0).
Abaixo do BOOTSTRAP_N o prior domina; acima, a evidência empírica domina.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.models.property import Property, PropertyChange

BOOTSTRAP_N = 30
MODEL_VERSION = "v1_heuristic"
HORIZONS = (30, 60, 90)


@dataclass
class PricePredictionResult:
    property_id: str
    horizon: int
    probability: float
    expected_drop_pct: float
    model_version: str
    basis: dict[str, Any] = field(default_factory=dict)


def _load_priors() -> dict:
    path = Path(__file__).parent / "priors.yaml"
    with open(path) as fh:
        return yaml.safe_load(fh)


def _get_prior(priors: dict, bank_code: str, modality: str, horizon: int) -> tuple[float, float]:
    key = f"horizon_{horizon}"
    modal = priors.get("banks", {}).get(bank_code, {}).get("modalities", {}).get(modality, {})
    if key in modal:
        e = modal[key]
        return float(e["probability"]), float(e["expected_drop_pct"])
    d = priors["default"][key]
    return float(d["probability"]), float(d["expected_drop_pct"])


def _empirical_stats(
    session: Session, bank_id: Any, modality: str, horizon: int
) -> tuple[int, float | None, float | None]:
    """Returns (n, drop_probability, avg_drop_pct) from historical data."""
    props = (
        session.query(Property)
        .filter(Property.bank_id == bank_id, Property.sale_modality == modality)
        .all()
    )
    if not props:
        return 0, None, None

    deadline = timedelta(days=horizon)
    dropped = 0
    drop_pcts: list[float] = []

    for p in props:
        cutoff = p.first_seen_at + deadline
        changes = (
            session.query(PropertyChange)
            .filter(
                PropertyChange.property_id == p.id,
                PropertyChange.field_name == "current_value",
            )
            .all()
        )
        for c in changes:
            # Handle both tz-aware and tz-naive comparisons
            det = c.detected_at
            cut = cutoff
            try:
                if det.tzinfo is None and cut.tzinfo is not None:
                    from datetime import timezone
                    det = det.replace(tzinfo=timezone.utc)
                elif det.tzinfo is not None and cut.tzinfo is None:
                    from datetime import timezone
                    cut = cut.replace(tzinfo=timezone.utc)
            except AttributeError:
                pass

            if det <= cut:
                try:
                    old_v = float(c.old_value)
                    new_v = float(c.new_value)
                    if new_v < old_v and old_v > 0:
                        dropped += 1
                        drop_pcts.append((old_v - new_v) / old_v * 100)
                        break
                except (TypeError, ValueError):
                    pass

    n = len(props)
    prob = dropped / n if n > 0 else None
    avg_drop = sum(drop_pcts) / len(drop_pcts) if drop_pcts else None
    return n, prob, avg_drop


def compute_predictions(session: Session, prop: Property) -> list[PricePredictionResult]:
    priors = _load_priors()
    bank_code = prop.bank.code if prop.bank else "unknown"
    modality = prop.sale_modality
    results = []

    for horizon in HORIZONS:
        prior_prob, prior_drop = _get_prior(priors, bank_code, modality, horizon)
        n, emp_prob, emp_drop = _empirical_stats(session, prop.bank_id, modality, horizon)

        w = min(n / BOOTSTRAP_N, 1.0)
        if emp_prob is not None:
            probability = (1 - w) * prior_prob + w * emp_prob
            expected_drop = (1 - w) * prior_drop + w * (emp_drop or prior_drop)
        else:
            probability = prior_prob
            expected_drop = prior_drop

        results.append(PricePredictionResult(
            property_id=str(prop.id),
            horizon=horizon,
            probability=round(min(max(probability, 0.0), 1.0), 4),
            expected_drop_pct=round(expected_drop, 2),
            model_version=MODEL_VERSION,
            basis={
                "bank_code": bank_code,
                "modality": modality,
                "prior_probability": prior_prob,
                "prior_expected_drop_pct": prior_drop,
                "empirical_n": n,
                "empirical_probability": emp_prob,
                "blend_weight": w,
            },
        ))

    return results
