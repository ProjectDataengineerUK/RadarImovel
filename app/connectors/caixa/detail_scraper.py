"""
Scraping da página de detalhe da Caixa.

Extrai campos não disponíveis no CSV: CEP, foto, áreas estruturadas,
quartos, garagem, edital, data do leilão, leiloeiro, ocupação.
"""
import re
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.logging import logger

CAIXA_DETAIL_BASE = "https://venda-imoveis.caixa.gov.br"

_RE_CEP = re.compile(r"CEP:\s*(\d{5}-\d{3})")
_RE_AREA = re.compile(r"rea\s+(?:total|privativa|do terreno)\s*=\s*([\d,\.]+)m", re.I)
_RE_AREA_LABEL = re.compile(r"rea\s+(total|privativa|do terreno)\s*=\s*([\d,\.]+)m", re.I)
_RE_DATE = re.compile(r"(\d{2}/\d{2}/\d{4})")
_RE_DECIMAL = re.compile(r"[\d,\.]+")


def _to_decimal(value: str) -> Decimal | None:
    s = re.sub(r"[^\d,.]", "", value)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_date(text: str) -> date | None:
    m = _RE_DATE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d/%m/%Y").date()
    except ValueError:
        return None


class CaixaDetailScraper:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch(self, url: str) -> bytes:
        delay = self.settings.caixa_request_delay_ms / 1000
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RadarImovel/1.0)"}
        for attempt in range(1, self.settings.caixa_max_retries + 1):
            try:
                time.sleep(delay)
                resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
                resp.raise_for_status()
                if resp.content:
                    return resp.content
            except Exception as exc:
                logger.warning("caixa.detail.fetch_failed", url=url, attempt=attempt, error=str(exc))
        return b""

    def parse(self, html_bytes: bytes) -> dict:
        if not html_bytes:
            return {}

        soup = BeautifulSoup(html_bytes, "lxml", from_encoding="utf-8")
        text = soup.get_text(separator="\n")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        result: dict = {}

        # A página separa labels e valores em linhas distintas.
        # Itera sobre pares (linha atual, próxima linha) para capturar ambos os padrões.
        for i, ln in enumerate(lines):
            next_ln = lines[i + 1] if i + 1 < len(lines) else ""

            # CEP: aparece na linha do endereço completo
            m = _RE_CEP.search(ln)
            if m:
                result["zipcode"] = m.group(1)

            # Tipo de imóvel — label + valor na mesma linha OU próxima linha
            if "Tipo de im" in ln:
                val = ln.split(":", 1)[1].strip() if ":" in ln else ""
                result["property_type"] = val or next_ln

            # Quartos — label na linha, valor na próxima
            if ln.rstrip(":") == "Quartos" or ln.startswith("Quartos:"):
                raw = ln.split(":")[-1].strip() or next_ln
                try:
                    result["bedrooms"] = int(raw)
                except ValueError:
                    pass

            # Garagem — label na linha, valor na próxima
            if ln.rstrip(":") == "Garagem" or ln.startswith("Garagem:"):
                raw = ln.split(":")[-1].strip() or next_ln
                try:
                    result["parking_spaces"] = int(raw)
                except ValueError:
                    pass

            # Áreas: na página real o label fica em uma linha e o valor na próxima.
            # No HTML de testes label+valor estão na mesma linha ("=120,00m2").
            # Tenta inline primeiro; se não achar, usa próxima linha.
            if "rea total" in ln:
                m = re.search(r"=\s*([\d]+[,\.][\d]+)", ln) or re.search(r"^([\d]+[,\.][\d]+)", next_ln)
                v = _to_decimal(m.group(1)) if m else None
                if v:
                    result["area_total"] = v

            if "rea privativa" in ln:
                m = re.search(r"=\s*([\d]+[,\.][\d]+)", ln) or re.search(r"^([\d]+[,\.][\d]+)", next_ln)
                v = _to_decimal(m.group(1)) if m else None
                if v:
                    result["area_private"] = v

            # Edital: "Edital: 0012/0326 - CPVE/RE"
            if ln.startswith("Edital:"):
                result["edital_number"] = ln.split(":", 1)[1].strip()

            # Leiloeiro
            if ln.startswith("Leiloeiro"):
                result["auctioneer_name"] = ln.split(":", 1)[-1].strip()

            # Data do leilão: "Data da Licitação Aberta - 13/07/2026 - 10h00"
            if "Data da" in ln and "/" in ln:
                d = _parse_date(ln)
                if d:
                    result["auction_date"] = d

            # Situação do imóvel (removida da Caixa, mantida para regressão futura)
            if "Desocupado" in ln:
                result["occupancy_status"] = "Desocupado"
            elif "Ocupado" in ln and "occupancy_status" not in result:
                result["occupancy_status"] = "Ocupado"

        # Foto: primeira imagem dentro de /fotos/
        img = soup.find("img", src=re.compile(r"^/fotos/"))
        if img:
            result["photo_url"] = CAIXA_DETAIL_BASE + img["src"]

        return result

    def enrich(self, normalized: dict, detail_url: str) -> dict:
        """Busca e faz merge dos campos do detalhe no dict normalizado."""
        try:
            html = self.fetch(detail_url)
            detail = self.parse(html)
            if detail:
                normalized.update(detail)
                logger.info("caixa.detail.enriched", external_code=normalized.get("external_code"), fields=list(detail.keys()))
        except Exception as exc:
            logger.warning("caixa.detail.enrich_failed", url=detail_url, error=str(exc))
        return normalized
