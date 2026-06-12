from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureDef:
    key: str
    description: str


@dataclass(frozen=True)
class QuotaDef:
    key: str
    period: str  # "day" | "month" | "static"
    description: str


FEATURES: dict[str, FeatureDef] = {f.key: f for f in [
    FeatureDef("risk_score", "Score de risco multidimensional"),
    FeatureDef("due_diligence_pdf", "Relatório PDF de due diligence"),
    FeatureDef("export", "Export CSV/Excel"),
    FeatureDef("calculator", "Calculadora de viabilidade"),
    FeatureDef("portfolio", "Carteira Kanban"),
    FeatureDef("realtime_alerts", "Alertas em tempo real (<15min)"),
    FeatureDef("whatsapp_channel", "Alertas por WhatsApp"),
    FeatureDef("ask", "Pergunte ao edital (RAG)"),
    FeatureDef("price_forecast", "Curva de desconto preditiva"),
    FeatureDef("api_access", "API B2B"),
]}

QUOTAS: dict[str, QuotaDef] = {q.key: q for q in [
    QuotaDef("alerts_per_day", "day", "Alertas enviados por dia"),
    QuotaDef("watchlists", "static", "Watchlists ativas"),
    QuotaDef("dd_reports_per_month", "month", "Relatórios due diligence/mês"),
    QuotaDef("ask_per_day", "day", "Perguntas ao edital/dia"),
]}

# Planos padrão com features e limites pré-definidos
DEFAULT_PLANS: list[dict] = [
    {
        "code": "free",
        "name": "Free",
        "price_brl": 0,
        "features": {
            "risk_score": False,
            "due_diligence_pdf": False,
            "export": False,
            "calculator": False,
            "portfolio": False,
            "realtime_alerts": False,
            "whatsapp_channel": False,
            "ask": False,
            "price_forecast": False,
            "api_access": False,
        },
        "limits": {
            "alerts_per_day": 5,
            "watchlists": 2,
            "dd_reports_per_month": 0,
            "ask_per_day": 0,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "price_brl": 7900,  # R$79,00 em centavos
        "features": {
            "risk_score": True,
            "due_diligence_pdf": False,
            "export": True,
            "calculator": True,
            "portfolio": True,
            "realtime_alerts": True,
            "whatsapp_channel": False,
            "ask": False,
            "price_forecast": False,
            "api_access": False,
        },
        "limits": {
            "alerts_per_day": 50,
            "watchlists": 10,
            "dd_reports_per_month": 0,
            "ask_per_day": 0,
        },
    },
    {
        "code": "premium",
        "name": "Premium",
        "price_brl": 19900,  # R$199,00 em centavos
        "features": {
            "risk_score": True,
            "due_diligence_pdf": True,
            "export": True,
            "calculator": True,
            "portfolio": True,
            "realtime_alerts": True,
            "whatsapp_channel": True,
            "ask": True,
            "price_forecast": True,
            "api_access": False,
        },
        "limits": {
            "alerts_per_day": 200,
            "watchlists": 50,
            "dd_reports_per_month": 5,
            "ask_per_day": 20,
        },
    },
]


def validate_plan_config(features: dict, limits: dict) -> list[str]:
    errors = [f"flag desconhecida: {k}" for k in features if k not in FEATURES]
    errors += [f"quota desconhecida: {k}" for k in limits if k not in QUOTAS]
    return errors
