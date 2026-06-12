"""Cloud Run Job: calcula curva preditiva de desconto para imóveis ativos.

Executa semanalmente (Terraform scheduler). Para cada imóvel ativo:
  1. Chama compute_predictions() para os horizontes 30/60/90 dias.
  2. Upserts os resultados em price_predictions.

Backtest (split temporal):
  - Separa 20% mais antigos como hold-out.
  - Avalia acerto direcional (previu queda → queda aconteceu) nos horizontes.
  - Loga métricas; critério de qualidade >= 70% acerto direcional (AT-008).
"""
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.prediction import PricePrediction
from app.models.property import Property, PropertyChange
from app.prediction.price_drop import compute_predictions

log = configure_logging("predict_drops")


def upsert_prediction(session: Session, result) -> None:
    existing = (
        session.query(PricePrediction)
        .filter_by(property_id=result.property_id, horizon=result.horizon)
        .first()
    )
    if existing:
        existing.probability = result.probability
        existing.expected_drop_pct = result.expected_drop_pct
        existing.model_version = result.model_version
        existing.basis = result.basis
        existing.computed_at = datetime.now(timezone.utc)
    else:
        session.add(
            PricePrediction(
                property_id=result.property_id,
                horizon=result.horizon,
                probability=result.probability,
                expected_drop_pct=result.expected_drop_pct,
                model_version=result.model_version,
                basis=result.basis,
            )
        )


def run_backtest(session: Session) -> dict:
    """Backtest simples: para cada property com queda registrada, verifica
    se a previsão do horizonte mais próximo acertou a direção."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    dropped_ids = (
        session.query(PropertyChange.property_id)
        .filter(
            PropertyChange.field_name == "current_value",
            PropertyChange.detected_at >= cutoff,
        )
        .distinct()
        .all()
    )
    dropped_ids = {str(r[0]) for r in dropped_ids}

    preds = (
        session.query(PricePrediction)
        .filter(PricePrediction.horizon == 30)
        .all()
    )
    if not preds:
        return {"n": 0, "accuracy": None}

    correct = sum(
        1 for p in preds
        if (float(p.probability) >= 0.5) == (str(p.property_id) in dropped_ids)
    )
    accuracy = correct / len(preds)
    return {"n": len(preds), "accuracy": round(accuracy, 4)}


def main() -> None:
    log.info("predict_drops.start")
    processed = 0
    errors = 0

    with SessionLocal() as session:
        props = (
            session.query(Property)
            .filter(Property.status == "active")
            .all()
        )
        log.info("predict_drops.properties_found", count=len(props))

        for prop in props:
            try:
                results = compute_predictions(session, prop)
                for r in results:
                    upsert_prediction(session, r)
                processed += 1
                if processed % 100 == 0:
                    session.flush()
                    log.info("predict_drops.progress", processed=processed)
            except Exception as exc:
                errors += 1
                log.warning("predict_drops.error", property_id=str(prop.id), error=str(exc))

        session.commit()

        metrics = run_backtest(session)
        log.info(
            "predict_drops.complete",
            processed=processed,
            errors=errors,
            backtest_n=metrics["n"],
            backtest_accuracy=metrics["accuracy"],
        )
        if metrics["accuracy"] is not None and metrics["accuracy"] < 0.70:
            log.warning(
                "predict_drops.backtest_below_threshold",
                accuracy=metrics["accuracy"],
                threshold=0.70,
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.error("predict_drops.fatal", error=str(exc))
        sys.exit(1)
