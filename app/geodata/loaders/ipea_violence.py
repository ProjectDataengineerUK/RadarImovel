import io
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import sqlalchemy as sa

from app.geodata.loaders.base import GeoLoader, LayerStats

IPEA_URL = "https://www.ipea.gov.br/atlasviolencia/download/24/atlas-da-violencia-2023-microdados"
SOURCE = "IPEA Atlas da Violência 2023"
CSV_PATH = Path("data/atlas_violencia.csv")

_CODE_COLS = ["codmun", "cod_mun", "CodMun", "ibge_code", "Codmun7", "geocodigo"]
_RATE_PATTERN = re.compile(r"taxa.*homicid|homicid.*taxa", re.IGNORECASE)


def _find_code_col(df: pd.DataFrame) -> str | None:
    for c in _CODE_COLS:
        if c in df.columns:
            return c
    return None


def _find_rate_col(df: pd.DataFrame) -> str | None:
    # Prefer most recent year column matching the pattern
    year_cols = [c for c in df.columns if _RATE_PATTERN.search(c) and re.search(r"20\d\d", c)]
    if year_cols:
        return sorted(year_cols)[-1]
    # Fall back to any column matching the pattern
    return next((c for c in df.columns if _RATE_PATTERN.search(c)), None)


class IpeaViolenceLoader(GeoLoader):
    """Downloads IPEA Atlas da Violência, extracts homicide rates, writes CSV, updates DB."""

    def load(self, session: Any, gcs_bucket: str | None = None, **kwargs: Any) -> LayerStats:
        errors: list[str] = []
        try:
            resp = requests.get(IPEA_URL, timeout=120)
            resp.raise_for_status()
            df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, dtype=str)
        except Exception as exc:
            return LayerStats("ipea_violence", 0, SOURCE, errors=[str(exc)])

        code_col = _find_code_col(df)
        rate_col = _find_rate_col(df)
        if not code_col or not rate_col:
            return LayerStats(
                "ipea_violence",
                0,
                SOURCE,
                errors=[f"Colunas não encontradas. Disponíveis: {list(df.columns)[:15]}"],
            )

        csv_rows: list[dict] = []
        db_rows: list[dict] = []

        for _, row in df.iterrows():
            code = str(row[code_col]).strip().split(".")[0]
            if not re.match(r"^\d{6,7}$", code):
                continue
            try:
                rate = float(str(row[rate_col]).replace(",", "."))
            except (ValueError, TypeError):
                continue

            year_match = re.search(r"20\d\d", rate_col)
            year = year_match.group() if year_match else "2022"
            csv_rows.append({"ibge_code": code, "year": year, "homicide_rate": str(rate)})

            # Only update DB for 7-digit codes (IBGE standard)
            code7 = code if len(code) == 7 else None
            if code7:
                db_rows.append({"ibge_code": code7, "homicide_rate": rate})

        # Write local CSV (read by IpeaAtlas via lru_cache)
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(csv_rows).to_csv(CSV_PATH, index=False)

        # Upload to GCS for container availability
        if gcs_bucket:
            try:
                from google.cloud import storage

                client = storage.Client()
                blob = client.bucket(gcs_bucket).blob("reference/atlas_violencia.csv")
                blob.upload_from_filename(str(CSV_PATH))
            except Exception as exc:
                errors.append(f"GCS upload: {exc}")

        if db_rows:
            session.execute(
                sa.text(
                    "INSERT INTO ibge_municipality_stats"
                    " (ibge_code, name, state, homicide_rate, updated_at)"
                    " VALUES (:ibge_code, '', '', :homicide_rate, now())"
                    " ON CONFLICT (ibge_code) DO UPDATE SET"
                    "  homicide_rate = EXCLUDED.homicide_rate, updated_at = now()"
                ),
                db_rows,
            )
            session.commit()

        return LayerStats(
            layer_type="ipea_violence",
            polygons_loaded=len(csv_rows),
            source=SOURCE,
            errors=errors,
        )
