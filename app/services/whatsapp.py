"""Canal WhatsApp via Meta Cloud API (Business Platform v20.0).

Envia template de mensagem pré-aprovado. O template `radar_alerta_imovel`
deve estar criado e aprovado no painel Meta Business antes de usar em prod.
"""
from __future__ import annotations

import httpx
from app.core.logging import logger
from app.services.notification import NotificationChannel

_API_BASE = "https://graph.facebook.com/v20.0"


class WhatsAppChannel(NotificationChannel):
    def __init__(self, phone_number_id: str, access_token: str):
        self._phone_number_id = phone_number_id
        self._token = access_token

    async def send(self, chat_id: str, message: str) -> bool:
        """chat_id deve ser o número E.164 (ex: +5511999999999)."""
        url = f"{_API_BASE}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": chat_id.lstrip("+"),
            "type": "template",
            "template": {
                "name": "radar_alerta_imovel",
                "language": {"code": "pt_BR"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": message[:1024]}],
                    }
                ],
            },
        }
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
                ok = resp.status_code == 200
                if not ok:
                    logger.warning("whatsapp.send_failed", to=chat_id, status=resp.status_code, body=resp.text[:200])
                return ok
        except Exception as exc:
            logger.error("whatsapp.send_error", to=chat_id, error=str(exc))
            return False
