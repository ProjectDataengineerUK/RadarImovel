"""Playwright fetch utility shared by SPA-rendered bank connectors."""
import os

from app.core.logging import logger

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def fetch_with_playwright(
    url: str,
    wait_until: str = "networkidle",
    timeout_ms: int = 30_000,
) -> bytes:
    """Render a URL with headless Chromium and return the full page HTML.

    Returns b"" when Playwright is unavailable (not installed or DISABLE_PLAYWRIGHT=true).
    Callers should fall back to httpx when this returns empty.
    """
    if os.environ.get("DISABLE_PLAYWRIGHT", "").lower() == "true":
        return b""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright.not_installed", url=url)
        return b""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(user_agent=_USER_AGENT, locale="pt-BR")
            page = context.new_page()
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            content = page.content().encode("utf-8")
            browser.close()
            logger.info("playwright.fetch_ok", url=url, size=len(content))
            return content
    except Exception as exc:
        logger.error("playwright.fetch_failed", url=url, error=str(exc))
        return b""
