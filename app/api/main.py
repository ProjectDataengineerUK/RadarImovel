from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import properties, watchlists, users, alerts, admin, risk
from app.api.routes import admin_plans, admin_users, admin_audit, admin_metrics
from app.api.routes import calculator, admin_costs, portfolio, admin_dedup
from app.api.routes import ask, radar_index

settings = get_settings()

app = FastAPI(
    title="Radar Imóvel API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(watchlists.router)
app.include_router(users.router)
app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(risk.router)
app.include_router(admin_plans.router)
app.include_router(admin_users.router)
app.include_router(admin_audit.router)
app.include_router(admin_metrics.router)
app.include_router(calculator.router)
app.include_router(admin_costs.router)
app.include_router(portfolio.router)
app.include_router(admin_dedup.router)
app.include_router(ask.router)
app.include_router(radar_index.router)


@app.get("/health")
def health():
    return {"status": "ok"}
