"""Canal push via Firebase Cloud Messaging (FCM) HTTP v1 API."""
from __future__ import annotations

import httpx
from app.core.logging import logger
from app.services.notification import NotificationChannel

_FCM_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


class PushChannel(NotificationChannel):
    def __init__(self, project_id: str, access_token: str):
        self._url = _FCM_URL.format(project_id=project_id)
        self._token = access_token

    async def send(self, chat_id: str, message: str) -> bool:
        """chat_id é o FCM registration token do dispositivo."""
        payload = {
            "message": {
                "token": chat_id,
                "notification": {
                    "title": "Radar Imóvel — Novo imóvel",
                    "body": message[:200],
                },
                "data": {"source": "radar_imovel"},
            }
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=payload, headers=headers)
                ok = resp.status_code == 200
                if not ok:
                    logger.warning("push.send_failed", token=chat_id[:12], status=resp.status_code)
                return ok
        except Exception as exc:
            logger.error("push.send_error", token=chat_id[:12], error=str(exc))
            return False
