from abc import ABC, abstractmethod
import httpx
from app.core.logging import logger


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
                    logger.warning(
                        "telegram.send_failed",
                        chat_id=chat_id,
                        status=response.status_code,
                    )
                return ok
        except Exception as exc:
            logger.error("telegram.send_error", chat_id=chat_id, error=str(exc))
            return False
