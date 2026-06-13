"""Parser HTML Banrisul — ASPX listings (ISO-8859-1).

Real row structure (td.bloco cells, 6 cols):
  [date_publicacao, licitacao_number (linked), modalidade, objeto, data_abertura, ""]

detail URL: /bob/link/bobw10hn_leiloes_comprar_detalhe.aspx?cat=AVISO&numero=XXXXX
"""
import re
from collections.abc import Iterator

from bs4 import BeautifulSoup

from app.connectors.base import RawProperty
from app.core.logging import logger

_DETAIL_BASE = "https://www.banrisul.com.br/bob/link/"
_EDITAL_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


class BanrisulParser:
    BANK_CODE = "banrisul"

    def parse(self, raw_bytes: bytes, source_url: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("banrisul.parser.empty_bytes", source_url=source_url)
            return
        try:
            # ASPX pages are ISO-8859-1
            text = raw_bytes.decode("iso-8859-1")
            soup = BeautifulSoup(text, "lxml")
        except Exception as exc:
            logger.error("banrisul.parser.soup_failed", source_url=source_url, error=str(exc))
            return

        rows = soup.find_all("tr")
        found = 0
        for row in rows:
            tds = row.find_all("td", class_="bloco")
            if not tds:
                continue
            try:
                texts = [td.get_text(" ", strip=True) for td in tds]
                # columns: date_pub, licitacao, modalidade, objeto, abertura, (empty)
                if len(texts) < 5:
                    continue

                date_pub = texts[0]
                licitacao = texts[1]
                modalidade = texts[2]
                objeto = texts[3]
                abertura = texts[4]

                # Link to detail page is on the licitacao cell
                link_tag = tds[1].find("a", href=True) if len(tds) > 1 else None
                if link_tag:
                    href = str(link_tag["href"]).strip()
                    detail_url = (
                        href if href.startswith("http") else _DETAIL_BASE + href.lstrip("/")
                    )
                else:
                    detail_url = source_url

                # External URL mentioned in objeto (pregaobanrisul.com.br/...)
                edital_url: str | None = None
                m = _EDITAL_URL_RE.search(objeto)
                if m:
                    edital_url = m.group(0).rstrip(".")

                external_code = licitacao.replace("/", "_").strip() or f"banrisul-{found}"

                raw_data: dict = {
                    "external_code": external_code,
                    "title": objeto,
                    "sale_modality": modalidade,
                    "date_published": date_pub,
                    "auction_date": abertura,
                    "state": "RS",
                    "edital_url": edital_url,
                    "official_url": detail_url,
                }

                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code=self.BANK_CODE,
                    source_name="banrisul_aspx",
                )
                found += 1
            except Exception as exc:
                logger.error("banrisul.parser.row_failed", error=str(exc))

        if found == 0:
            logger.warning("banrisul.parser.no_listings", source_url=source_url)
        else:
            logger.info("banrisul.parser.done", count=found, source_url=source_url)
