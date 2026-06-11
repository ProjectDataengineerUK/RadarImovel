"""IPEA Atlas da Violência — CSV local carregado em memória."""
from __future__ import annotations

import functools
from pathlib import Path


@functools.lru_cache(maxsize=1)
def _load_atlas() -> dict[str, dict]:
    csv_path = Path(__file__).parent.parent.parent.parent / "data" / "atlas_violencia.csv"
    if not csv_path.exists():
        return {}
    import csv

    data: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("ibge_code", "").strip()
            if code:
                data[code] = {
                    "homicide_rate": float(row["homicide_rate"]) if row.get("homicide_rate") else None,
                    "year": int(row["year"]) if row.get("year") else None,
                }
    return data


class IpeaAtlas:
    def get_homicide_rate(self, ibge_code: str) -> float | None:
        atlas = _load_atlas()
        entry = atlas.get(ibge_code)
        return entry["homicide_rate"] if entry else None
