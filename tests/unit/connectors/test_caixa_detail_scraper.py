from datetime import date
from decimal import Decimal

from app.connectors.caixa.detail_scraper import CaixaDetailScraper

SAMPLE_HTML = (
    b"<html><body>"
    b"<span>Tipo de im\xc3\xb3vel:Apartamento</span>"
    b"<span>Quartos:3</span>"
    b"<span>Garagem:2</span>"
    b"<span>\xc3\x81rea total =120,00m2</span>"
    b"<span>\xc3\x81rea privativa =95,50m2</span>"
    b"<span>Edital:\xc2\xa00012/0326 - CPVE/RE</span>"
    b"<span>Leiloeiro(a): MARIA SILVA</span>"
    b"<span>Data da Licita\xc3\xa7\xc3\xa3o Aberta - 13/07/2026 - 10h00</span>"
    b"<span>Endere\xc3\xa7o: RUA DAS FLORES, N. 10, CEP: 01310-100, SAO PAULO - SP</span>"
    b"<img src='/fotos/F123456.jpg' />"
    b"<!--span>Situa\xc3\xa7\xc3\xa3o: <strong>Desocupado</strong></span><br-->"
    b"</body></html>"
)

SAMPLE_HTML_OCUPADO = (
    b"<html><body>"
    b"<!--span>Situa\xc3\xa7\xc3\xa3o: <strong>Ocupado</strong></span><br-->"
    b"</body></html>"
)


def test_parse_zipcode():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["zipcode"] == "01310-100"


def test_parse_bedrooms():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["bedrooms"] == 3


def test_parse_parking():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["parking_spaces"] == 2


def test_parse_area_total():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["area_total"] == Decimal("120.00")


def test_parse_area_private():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["area_private"] == Decimal("95.50")


def test_parse_edital():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert "0012/0326" in result["edital_number"]


def test_parse_auctioneer():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["auctioneer_name"] == "MARIA SILVA"


def test_parse_auction_date():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["auction_date"] == date(2026, 7, 13)


def test_parse_photo_url():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["photo_url"].endswith("/fotos/F123456.jpg")


def test_parse_occupancy_desocupado():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["occupancy_status"] == "Desocupado"


def test_parse_occupancy_ocupado():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML_OCUPADO)
    assert result["occupancy_status"] == "Ocupado"


def test_parse_empty_returns_empty():
    scraper = CaixaDetailScraper()
    assert scraper.parse(b"") == {}


def test_parse_property_type():
    scraper = CaixaDetailScraper()
    result = scraper.parse(SAMPLE_HTML)
    assert result["property_type"] == "Apartamento"
