"""Dimensão A — Jurídico: processos CNJ (execução, inventário, penhora, usucapião)."""
import unicodedata
from datetime import date

from app.risk.schemas import DimensionScore, RiskIndicator
from app.risk.sources.cnj import CnjClient


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def score_juridico(
    cnpj_owner: str | None,
    address: str,
    city: str,
    state: str,
    cnj_client: CnjClient,
) -> DimensionScore:
    indicators: list[RiskIndicator] = []
    points = 0.0
    partial = False

    try:
        processos = cnj_client.search(
            cnpj=cnpj_owner,
            address=address,
            city=city,
            state=state,
        )
    except Exception:
        partial = True
        processos = []

    ativos = [p for p in processos if p.get("status") == "ativo"]

    if ativos:
        points += min(len(ativos) * 10, 40)
        indicators.append(
            RiskIndicator(
                code="A1",
                value=len(ativos),
                source="CNJ Datajud",
                date_fetched=date.today(),
            )
        )

    inv = [p for p in ativos if "inventar" in _norm(p.get("classe", ""))]
    if inv:
        points += 15
        indicators.append(
            RiskIndicator(
                code="A2",
                value=len(inv),
                source="CNJ Datajud",
                date_fetched=date.today(),
                note="inventário/herança identificado",
            )
        )

    exec_fiscal = [p for p in ativos if "execu" in _norm(p.get("classe", ""))]
    if exec_fiscal:
        points += 15
        indicators.append(
            RiskIndicator(
                code="A3",
                value=len(exec_fiscal),
                source="CNJ Datajud",
                date_fetched=date.today(),
                note="execução fiscal",
            )
        )

    return DimensionScore(
        code="A",
        name="juridico",
        raw_points=min(points, 100),
        indicators=indicators,
        partial=partial,
    )
