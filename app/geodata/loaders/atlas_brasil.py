import io
import re
from typing import Any

import pandas as pd
import requests
import sqlalchemy as sa

from app.geodata.loaders.base import GeoLoader, LayerStats

# Atlas Brasil 2013 — official PNUD/FJP/IPEA dataset with IDH-M 2010 for all municipalities
ATLAS_URL = "http://www.atlasbrasil.org.br/dados/raw/atlas2013_dadosbrutos_pt.xls"
SOURCE = "Atlas Brasil 2013 — PNUD/FJP/IPEA"

_CODE_COLS = ["Codmun7", "codmun7", "CODMUN7", "cod_mun", "Código"]
_IDH_COLS = ["IDHM", "idhm", "IDH-M 2010", "IDHM 2010"]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        for cand in candidates:
            if cand.lower() in c.lower():
                return c
    return None


class AtlasBrasilLoader(GeoLoader):
    """Reads municipal IDH from Atlas Brasil XLS and updates ibge_municipality_stats."""

    def load(self, session: Any, **kwargs: Any) -> LayerStats:
        errors: list[str] = []
        try:
            resp = requests.get(ATLAS_URL, timeout=120)
            resp.raise_for_status()
            df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, dtype=str)
        except Exception as exc:
            return LayerStats("atlas_brasil", 0, SOURCE, errors=[str(exc)])

        code_col = _find_col(df, _CODE_COLS)
        idh_col = _find_col(df, _IDH_COLS)
        if not code_col or not idh_col:
            return LayerStats(
                "atlas_brasil",
                0,
                SOURCE,
                errors=[f"Colunas não encontradas. Disponíveis: {list(df.columns)[:15]}"],
            )

        rows = []
        for _, row in df.iterrows():
            code = str(row[code_col]).strip().split(".")[0]
            if not re.match(r"^\d{7}$", code):
                continue
            try:
                idh = float(str(row[idh_col]).replace(",", "."))
                if not (0.0 <= idh <= 1.0):
                    continue
            except (ValueError, TypeError):
                errors.append(f"IDH inválido para {code}: {row[idh_col]!r}")
                continue
            rows.append({"ibge_code": code, "idh": idh})

        if rows:
            session.execute(
                sa.text(
                    "INSERT INTO ibge_municipality_stats (ibge_code, name, state, idh, updated_at)"
                    " VALUES (:ibge_code, '', '', :idh, now())"
                    " ON CONFLICT (ibge_code) DO UPDATE SET"
                    "  idh = EXCLUDED.idh, updated_at = now()"
                ),
                rows,
            )
            session.commit()

        return LayerStats(
            layer_type="atlas_brasil",
            polygons_loaded=len(rows),
            source=SOURCE,
            errors=errors[:20],
        )
