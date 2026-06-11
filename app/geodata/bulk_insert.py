import json
from typing import Any

import sqlalchemy as sa


def bulk_insert_geodata(
    session: Any,
    layer_type: str,
    features: list[dict],
    source: str,
) -> int:
    """DELETE existing layer_type + INSERT batch. Idempotent."""
    session.execute(
        sa.text("DELETE FROM risk_geodata_layers WHERE layer_type = :lt"),
        {"lt": layer_type},
    )
    if not features:
        return 0

    from shapely import to_wkt

    rows = [
        {
            "lt": layer_type,
            "name": (f.get("name") or "")[:200],
            "attrs": json.dumps(f.get("attributes") or {}),
            "source": source,
            "geom": to_wkt(f["geom"]),
        }
        for f in features
        if f.get("geom") is not None and not f["geom"].is_empty
    ]

    if rows:
        session.execute(
            sa.text(
                "INSERT INTO risk_geodata_layers"
                " (id, layer_type, name, attributes, source, geom)"
                " VALUES (uuid_generate_v4(), :lt, :name, :attrs::jsonb, :source,"
                " ST_GeomFromText(:geom, 4326))"
            ),
            rows,
        )
    return len(rows)


def upsert_municipality_stats(session: Any, rows: list[dict]) -> int:
    """INSERT ... ON CONFLICT (ibge_code) DO UPDATE. COALESCE preserves existing non-null values."""
    if not rows:
        return 0
    session.execute(
        sa.text(
            "INSERT INTO ibge_municipality_stats"
            " (ibge_code, name, state, idh, homicide_rate, population_2022,"
            "  population_2010, avg_household_income, vacancy_rate, updated_at)"
            " VALUES (:ibge_code, :name, :state, :idh, :homicide_rate, :population_2022,"
            "  :population_2010, :avg_household_income, :vacancy_rate, now())"
            " ON CONFLICT (ibge_code) DO UPDATE SET"
            "  name             = CASE WHEN EXCLUDED.name != '' THEN EXCLUDED.name"
            "                         ELSE ibge_municipality_stats.name END,"
            "  state            = CASE WHEN EXCLUDED.state != '' THEN EXCLUDED.state"
            "                         ELSE ibge_municipality_stats.state END,"
            "  idh              = COALESCE(EXCLUDED.idh, ibge_municipality_stats.idh),"
            "  homicide_rate    = COALESCE(EXCLUDED.homicide_rate, ibge_municipality_stats.homicide_rate),"
            "  population_2022  = COALESCE(EXCLUDED.population_2022, ibge_municipality_stats.population_2022),"
            "  population_2010  = COALESCE(EXCLUDED.population_2010, ibge_municipality_stats.population_2010),"
            "  avg_household_income = COALESCE(EXCLUDED.avg_household_income, ibge_municipality_stats.avg_household_income),"
            "  vacancy_rate     = COALESCE(EXCLUDED.vacancy_rate, ibge_municipality_stats.vacancy_rate),"
            "  updated_at       = now()"
        ),
        rows,
    )
    return len(rows)
