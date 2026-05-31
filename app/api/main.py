from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import properties, watchlists, users, alerts, admin

settings = get_settings()

app = FastAPI(
    title="Radar Imóvel API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
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


@app.get("/health")
def health():
    return {"status": "ok"}
