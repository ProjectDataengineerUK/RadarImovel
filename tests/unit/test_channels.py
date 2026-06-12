"""AT-010: Canais de notificação (unit tests com mock de HTTP)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notification import TelegramChannel, build_channels


# ── TelegramChannel ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_telegram_send_success():
    ch = TelegramChannel(token="test_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await ch.send("123456", "Hello world")

    assert result is True


@pytest.mark.asyncio
async def test_telegram_send_failure():
    ch = TelegramChannel(token="bad_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await ch.send("123456", "Hello")

    assert result is False


@pytest.mark.asyncio
async def test_telegram_send_exception():
    ch = TelegramChannel(token="test")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))
        mock_client_cls.return_value = mock_client

        result = await ch.send("123456", "Hello")

    assert result is False


# ── WhatsAppChannel ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_whatsapp_send_success():
    from app.services.whatsapp import WhatsAppChannel
    ch = WhatsAppChannel("phone_id", "access_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await ch.send("+5511999999999", "Alerta imóvel")

    assert result is True


@pytest.mark.asyncio
async def test_whatsapp_strips_plus_sign():
    from app.services.whatsapp import WhatsAppChannel
    ch = WhatsAppChannel("phone_id", "token")

    captured = {}
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    async def fake_post(url, json=None, headers=None):
        captured["to"] = json["to"]
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_client_cls.return_value = mock_client

        await ch.send("+5511999999999", "msg")

    assert not captured["to"].startswith("+")


# ── EmailChannel ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_email_send_accepted():
    from app.services.email import EmailChannel
    ch = EmailChannel("SG.test_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 202  # SendGrid returns 202 on success

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await ch.send("user@test.com", "Alerta imóvel")

    assert result is True


# ── build_channels ─────────────────────────────────────────────────────────────

def test_build_channels_telegram_only():
    user = MagicMock()
    user.telegram_chat_id = 123456
    user.notification_channels = {}

    with patch("app.services.notification.get_settings") as mock_settings:
        mock_settings.return_value.telegram_bot_token = "tok"
        mock_settings.return_value.whatsapp_phone_number_id = ""
        mock_settings.return_value.sendgrid_api_key = ""
        mock_settings.return_value.fcm_project_id = ""

        channels = build_channels(user)

    assert len(channels) == 1
    from app.services.notification import TelegramChannel
    assert isinstance(channels[0][0], TelegramChannel)
    assert channels[0][1] == "123456"


def test_build_channels_no_channels_without_telegram():
    user = MagicMock()
    user.telegram_chat_id = None
    user.notification_channels = {}

    with patch("app.services.notification.get_settings") as mock_settings:
        mock_settings.return_value.telegram_bot_token = ""
        mock_settings.return_value.whatsapp_phone_number_id = ""
        mock_settings.return_value.sendgrid_api_key = ""
        mock_settings.return_value.fcm_project_id = ""

        channels = build_channels(user)

    assert channels == []


def test_build_channels_multichannel():
    user = MagicMock()
    user.telegram_chat_id = 999
    user.notification_channels = {
        "whatsapp": "+5511111111111",
        "email": "x@test.com",
    }

    with patch("app.services.notification.get_settings") as mock_settings:
        mock_settings.return_value.telegram_bot_token = "tok"
        mock_settings.return_value.whatsapp_phone_number_id = "phone_id"
        mock_settings.return_value.whatsapp_access_token = "wa_token"
        mock_settings.return_value.sendgrid_api_key = "sg_key"
        mock_settings.return_value.fcm_project_id = ""

        channels = build_channels(user)

    assert len(channels) == 3  # telegram + whatsapp + email
    channel_types = [type(c).__name__ for c, _ in channels]
    assert "TelegramChannel" in channel_types
    assert "WhatsAppChannel" in channel_types
    assert "EmailChannel" in channel_types
