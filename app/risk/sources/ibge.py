"""IBGE lookup — tabela local `ibge_municipality_stats` (O(1) por ibge_code)."""
from sqlalchemy.orm import Session  # noqa: F401


class IbgeLookup:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_stats(self, ibge_code: str) -> dict | None:
        from sqlalchemy import text

        row = self._session.execute(
            text(
                "SELECT idh, homicide_rate, population_2022, population_2010, "
                "avg_household_income, vacancy_rate "
                "FROM ibge_municipality_stats WHERE ibge_code = :code"
            ),
            {"code": ibge_code},
        ).fetchone()
        if not row:
            return None
        return {
            "idh": float(row.idh) if row.idh is not None else None,
            "homicide_rate": float(row.homicide_rate) if row.homicide_rate is not None else None,
            "population_2022": row.population_2022,
            "population_2010": row.population_2010,
            "avg_household_income": float(row.avg_household_income) if row.avg_household_income is not None else None,
            "vacancy_rate": float(row.vacancy_rate) if row.vacancy_rate is not None else None,
        }
