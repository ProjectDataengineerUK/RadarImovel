from app.connectors.caixa.parser import CaixaParser


def test_parse_returns_all_rows(fake_csv_bytes):
    parser = CaixaParser()
    rows = list(parser.parse(fake_csv_bytes, "https://example.com/SP.csv", "SP"))
    assert len(rows) == 3


def test_parse_sets_bank_code(fake_csv_bytes):
    parser = CaixaParser()
    rows = list(parser.parse(fake_csv_bytes, "https://example.com/SP.csv", "SP"))
    assert all(r.bank_code == "caixa" for r in rows)


def test_parse_injects_uf(fake_csv_bytes):
    parser = CaixaParser()
    rows = list(parser.parse(fake_csv_bytes, "https://example.com/SP.csv", "SP"))
    assert all(r.raw_data["state"] == "SP" for r in rows)


def test_parse_external_code(fake_csv_bytes):
    parser = CaixaParser()
    rows = list(parser.parse(fake_csv_bytes, "https://example.com/SP.csv", "SP"))
    codes = {r.external_code for r in rows}
    assert codes == {"7654321", "7654322", "7654323"}


def test_parse_empty_bytes_returns_nothing():
    parser = CaixaParser()
    rows = list(parser.parse(b"", "https://example.com/SP.csv", "SP"))
    assert rows == []


def test_parse_source_name_includes_uf(fake_csv_bytes):
    parser = CaixaParser()
    rows = list(parser.parse(fake_csv_bytes, "https://example.com/SP.csv", "SP"))
    assert all(r.source_name == "caixa_lista_SP" for r in rows)
