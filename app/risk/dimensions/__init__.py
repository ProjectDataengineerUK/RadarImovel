from app.risk.dimensions.fiscal import score_fiscal
from app.risk.dimensions.fundiario import score_fundiario
from app.risk.dimensions.juridico import score_juridico
from app.risk.dimensions.mercado import score_mercado
from app.risk.dimensions.ocupacao import score_ocupacao
from app.risk.dimensions.socioeconomico import score_socioeconomico

__all__ = [
    "score_juridico",
    "score_fundiario",
    "score_fiscal",
    "score_ocupacao",
    "score_socioeconomico",
    "score_mercado",
]
