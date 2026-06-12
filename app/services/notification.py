"""Canal de notificação: interface base + factory multichannel.

A factory `build_channels(user)` lê `user.notification_channels` (JSON)
e retorna a lista de (channel, chat_id) prontos para envio.

Estrutura de `notification_channels`:
    {
      "telegram": "12345678",
      "whatsapp": "+5511999999999",
      "email": "user@example.com",
      "push": "<fcm_token>"
    }
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import httpx

from app.core.config import get_settings
from app.core.logging import logger

if TYPE_CHECKING:
    from app.models.user import User


class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, chat_id: str, message: str) -> bool: ...


class TelegramChannel(NotificationChannel):
    def __init__(self, token: str):
        self.token = token
        self._base_url = f"https://api.telegram.org/bot{token}"

    async def send(self, chat_id: str, message: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self._base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                )
                ok = response.status_code == 200
                if not ok:
                    logger.warning("telegram.send_failed", chat_id=chat_id, status=response.status_code)
                return ok
        except Exception as exc:
            logger.error("telegram.send_error", chat_id=chat_id, error=str(exc))
            return False


def build_channels(user: "User") -> list[tuple[NotificationChannel, str]]:
    """Constrói lista de (canal, destino) a partir das preferências do usuário.

    Sempre inclui Telegram se `telegram_chat_id` existir, independentemente de
    `notification_channels`. Os outros canais são opt-in via JSON.
    """
    settings = get_settings()
    result: list[tuple[NotificationChannel, str]] = []

    if user.telegram_chat_id:
        result.append((TelegramChannel(token=settings.telegram_bot_token), str(user.telegram_chat_id)))

    prefs: dict = user.notification_channels or {}

    if whatsapp_id := prefs.get("whatsapp"):
        if settings.whatsapp_phone_number_id and settings.whatsapp_access_token:
            from app.services.whatsapp import WhatsAppChannel
            result.append((
                WhatsAppChannel(settings.whatsapp_phone_number_id, settings.whatsapp_access_token),
                whatsapp_id,
            ))

    if email := prefs.get("email"):
        if settings.sendgrid_api_key:
            from app.services.email import EmailChannel
            result.append((EmailChannel(settings.sendgrid_api_key), email))

    if push_token := prefs.get("push"):
        if settings.fcm_project_id and settings.fcm_access_token:
            from app.services.push import PushChannel
            result.append((PushChannel(settings.fcm_project_id, settings.fcm_access_token), push_token))

    return result
