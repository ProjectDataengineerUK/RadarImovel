import httpx
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()
BASE_URL = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


async def set_webhook(webhook_url: str) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{BASE_URL}/setWebhook", json={"url": webhook_url})
        return r.status_code == 200


async def send_message(chat_id: int | str, text: str, parse_mode: str = "HTML") -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
            return r.status_code == 200
    except Exception as exc:
        logger.error("telegram.send_message_error", chat_id=chat_id, error=str(exc))
        return False


def parse_start_token(text: str) -> str | None:
    """Extrai token do comando /start TOKEN enviado pelo usuário."""
    parts = text.strip().split()
    if len(parts) == 2 and parts[0] == "/start":
        return parts[1]
    return None


def format_property_alert(prop: dict) -> str:
    score = prop.get("opportunity_score", 0)
    discount = prop.get("discount_percent", 0)
    city = prop.get("city", "")
    state = prop.get("state", "")
    value = prop.get("current_value", 0)
    modality = prop.get("sale_modality", "")
    occupancy = prop.get("occupancy_status", "")
    url = prop.get("official_url", "")

    return (
        f"🏠 <b>Novo imóvel detectado — Radar Imóvel</b>\n\n"
        f"📍 {city}/{state}\n"
        f"💰 R$ {float(value):,.2f} ({discount}% de desconto)\n"
        f"📋 {modality} | {occupancy}\n"
        f"⭐ Score: {score}/100\n\n"
        f"🔗 <a href='{url}'>Ver imóvel na Caixa</a>"
    )
