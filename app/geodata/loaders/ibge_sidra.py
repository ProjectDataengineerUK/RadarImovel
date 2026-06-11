from typing import Any

import requests
import sqlalchemy as sa

from app.geodata.loaders.base import GeoLoader, LayerStats

# SIDRA table 4709 = 2022 Census — resident population by municipality (N6)
# SIDRA table 9605 = 2022 Census — average household income (rendimento médio)
SIDRA_POPULATION_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4709"
    "/periodos/2022/variaveis/93?localidades=N6"
)
SIDRA_INCOME_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/9605"
    "/periodos/2022/variaveis/10084?localidades=N6"
)
SOURCE = "IBGE SIDRA — Censo 2022"


def _parse_sidra(data: list[dict]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for bloco in data:
        for serie in bloco.get("resultados", []):
            for s in serie.get("series", []):
                code = str(s["localidade"]["id"]).strip()
                val_str = next(iter(s.get("serie", {}).values()), None)
                try:
                    result[code] = float(val_str) if val_str and val_str not in ("...", "-") else None
                except (ValueError, TypeError):
                    result[code] = None
    return result


class IbgeSidraLoader(GeoLoader):
    """Fetches population 2022 and average household income from IBGE SIDRA API."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        errors: list[str] = []
        population: dict[str, float | None] = {}
        income: dict[str, float | None] = {}

        try:
            resp = requests.get(SIDRA_POPULATION_URL, timeout=60)
            resp.raise_for_status()
            population = _parse_sidra(resp.json())
        except Exception as exc:
            errors.append(f"SIDRA população: {exc}")

        try:
            resp = requests.get(SIDRA_INCOME_URL, timeout=60)
            resp.raise_for_status()
            income = _parse_sidra(resp.json())
        except Exception as exc:
            errors.append(f"SIDRA renda: {exc}")

        all_codes = set(population) | set(income)
        rows = []
        for code in all_codes:
            pop = population.get(code)
            inc = income.get(code)
            rows.append(
                {
                    "ibge_code": code,
                    "population_2022": int(pop) if pop is not None else None,
                    "avg_household_income": inc,
                }
            )

        if rows:
            session.execute(
                sa.text(
                    "INSERT INTO ibge_municipality_stats"
                    " (ibge_code, name, state, population_2022, avg_household_income, updated_at)"
                    " VALUES (:ibge_code, '', '', :population_2022, :avg_household_income, now())"
                    " ON CONFLICT (ibge_code) DO UPDATE SET"
                    "  population_2022     = COALESCE(EXCLUDED.population_2022,"
                    "                         ibge_municipality_stats.population_2022),"
                    "  avg_household_income = COALESCE(EXCLUDED.avg_household_income,"
                    "                         ibge_municipality_stats.avg_household_income),"
                    "  updated_at = now()"
                ),
                rows,
            )
            session.commit()

        return LayerStats(
            layer_type="ibge_sidra",
            polygons_loaded=len(rows),
            source=SOURCE,
            errors=errors,
        )
