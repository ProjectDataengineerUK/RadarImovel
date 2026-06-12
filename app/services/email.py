"""Canal e-mail via SendGrid Mail Send API v3."""
from __future__ import annotations

import httpx
from app.core.logging import logger
from app.services.notification import NotificationChannel

_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
_FROM_EMAIL = "alertas@radarimovel.com.br"
_FROM_NAME = "Radar Imóvel"


class EmailChannel(NotificationChannel):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def send(self, chat_id: str, message: str) -> bool:
        """chat_id é o endereço de e-mail do destinatário."""
        subject = "Novo imóvel encontrado — Radar Imóvel"
        html_body = f"<pre style='font-family:sans-serif'>{message}</pre>"
        payload = {
            "personalizations": [{"to": [{"email": chat_id}]}],
            "from": {"email": _FROM_EMAIL, "name": _FROM_NAME},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(_SENDGRID_URL, json=payload, headers=headers)
                ok = resp.status_code in (200, 202)
                if not ok:
                    logger.warning("email.send_failed", to=chat_id, status=resp.status_code)
                return ok
        except Exception as exc:
            logger.error("email.send_error", to=chat_id, error=str(exc))
            return False
