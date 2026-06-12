"""Cloud Run Job: constrói o Radar Index — índice mensal de deságio por estado/banco.

Executa no 1º de cada mês (Terraform scheduler). Agrega descontos de imóveis ativos
e grava resultados em radar_index. Também persiste um JSON no GCS para consumo público
sem autenticação (CDN-friendly).

Formato do JSON público:
{
  "period": "2026-06",
  "generated_at": "...",
  "entries": [
    {"state": "SP", "bank_code": null, "avg_discount_pct": 28.4, "sample_size": 4201},
    ...
  ]
}
"""
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.bank import Bank
from app.models.prediction import RadarIndex
from app.models.property import Property

log = configure_logging("build_radar_index")
settings = get_settings()


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _percentile_approx(values: list[float], p: float) -> float | None:
    if not values:
        return None
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    return sorted_v[min(idx, len(sorted_v) - 1)]


def _build_entries(session: Session, period: str) -> list[dict]:
    rows = (
        session.query(
            Property.state,
            Bank.code.label("bank_code"),
            Property.property_type,
            Property.discount_percent,
        )
        .join(Bank, Bank.id == Property.bank_id)
        .filter(
            Property.status == "active",
            Property.discount_percent.isnot(None),
        )
        .all()
    )

    # Agrupa por (state, bank_code, property_type) e calcula estatísticas
    from collections import defaultdict
    groups: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        v = float(row.discount_percent)
        groups[(row.state, row.bank_code, row.property_type)].append(v)
        groups[(row.state, row.bank_code, None)].append(v)    # agrega por bank
        groups[(row.state, None, row.property_type)].append(v)  # agrega por tipo
        groups[(row.state, None, None)].append(v)               # agrega tudo

    entries = []
    seen: set[tuple] = set()
    for (state, bank_code, property_type), values in groups.items():
        key = (state, str(bank_code), str(property_type))
        if key in seen or len(values) < 3:
            continue
        seen.add(key)
        avg = sum(values) / len(values)
        median = _percentile_approx(values, 50)
        p25 = _percentile_approx(values, 25)
        p75 = _percentile_approx(values, 75)
        entries.append({
            "period": period,
            "state": state,
            "bank_code": bank_code,
            "property_type": property_type,
            "sample_size": len(values),
            "avg_discount_pct": round(avg, 2),
            "median_discount_pct": round(median or avg, 2),
            "p25_discount_pct": round(p25, 2) if p25 is not None else None,
            "p75_discount_pct": round(p75, 2) if p75 is not None else None,
        })
    return entries


def _upsert_radar_index(session: Session, entries: list[dict]) -> int:
    count = 0
    for e in entries:
        existing = (
            session.query(RadarIndex)
            .filter_by(
                period=e["period"],
                state=e["state"],
                bank_code=e["bank_code"],
                property_type=e["property_type"],
            )
            .first()
        )
        if existing:
            existing.sample_size = e["sample_size"]
            existing.avg_discount_pct = Decimal(str(e["avg_discount_pct"]))
            existing.median_discount_pct = Decimal(str(e["median_discount_pct"]))
            existing.p25_discount_pct = Decimal(str(e["p25_discount_pct"])) if e["p25_discount_pct"] else None
            existing.p75_discount_pct = Decimal(str(e["p75_discount_pct"])) if e["p75_discount_pct"] else None
            existing.computed_at = datetime.now(timezone.utc)
        else:
            session.add(RadarIndex(
                period=e["period"],
                state=e["state"],
                bank_code=e["bank_code"],
                property_type=e["property_type"],
                sample_size=e["sample_size"],
                avg_discount_pct=Decimal(str(e["avg_discount_pct"])),
                median_discount_pct=Decimal(str(e["median_discount_pct"])),
                p25_discount_pct=Decimal(str(e["p25_discount_pct"])) if e["p25_discount_pct"] else None,
                p75_discount_pct=Decimal(str(e["p75_discount_pct"])) if e["p75_discount_pct"] else None,
            ))
        count += 1
    return count


def _publish_gcs(period: str, entries: list[dict]) -> None:
    try:
        from google.cloud import storage
        payload = {
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entries": [
                e for e in entries
                if e["bank_code"] is None and e["property_type"] is None
            ],
        }
        client = storage.Client()
        bucket = client.bucket(settings.gcs_bucket_raw)
        blob = bucket.blob(f"public/radar_index/{period}.json")
        blob.upload_from_string(
            json.dumps(payload, ensure_ascii=False, default=str),
            content_type="application/json",
        )
        blob.make_public()
        log.info("build_radar_index.gcs_published", period=period, path=blob.name)
    except Exception as exc:
        log.warning("build_radar_index.gcs_error", error=str(exc))


def main() -> None:
    period = _period()
    log.info("build_radar_index.start", period=period)

    with SessionLocal() as session:
        entries = _build_entries(session, period)
        log.info("build_radar_index.entries_computed", count=len(entries))

        upserted = _upsert_radar_index(session, entries)
        session.commit()
        log.info("build_radar_index.upserted", count=upserted)

    _publish_gcs(period, entries)
    log.info("build_radar_index.complete", period=period)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.error("build_radar_index.fatal", error=str(exc))
        sys.exit(1)
