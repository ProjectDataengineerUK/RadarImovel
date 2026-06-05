"""
Validação manual do conector Caixa.

Baixa o XLSX de uma UF, parseia e normaliza — sem banco nem GCP.
Uso:  python scripts/validate_caixa.py [UF]   (default: SP)
"""
import sys
import os

# garante que o package app/ seja encontrado sem instalar o projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# variáveis mínimas para get_settings() não explodir
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("PUBSUB_PROJECT_ID", "local")
os.environ.setdefault("PUBSUB_TOPIC_EVENTS", "local")
os.environ.setdefault("GCS_BUCKET_RAW", "local")

from app.connectors.caixa.collector import CaixaConnector  # noqa: E402

UF = (sys.argv[1] if len(sys.argv) > 1 else "SP").upper()


def main() -> None:
    connector = CaixaConnector(uf=UF)
    sources = connector.discover_sources()
    url = sources[0]
    print(f"\n[1/3] URL: {url}")

    raw = connector.fetch_raw(url)
    if not raw:
        print("ERRO: resposta vazia — URL pode ter mudado ou há bloqueio de IP.")
        sys.exit(1)
    print(f"[2/3] Download OK — {len(raw):,} bytes")

    rows = list(connector.parse(raw, url))
    if not rows:
        print("ERRO: nenhuma linha parseada — verifique o mapeamento de colunas.")
        sys.exit(1)
    print(f"[3/3] Parse OK — {len(rows)} imóveis encontrados\n")

    # normaliza os primeiros 3 para inspeção
    print("=== Amostra (3 primeiros imóveis normalizados) ===")
    for raw_prop in rows[:3]:
        try:
            n = connector.normalize(raw_prop)
            print(
                f"  [{n['external_code']}] {n['property_type']} | "
                f"{n['city']}/{n['state']} | "
                f"R$ {n['current_value']:,.0f} | "
                f"desc {n['discount_percent'] or 0:.1f}% | "
                f"{n['occupancy_status']}"
            )
        except Exception as exc:
            print(f"  ERRO ao normalizar {raw_prop.external_code}: {exc}")

    # estatísticas rápidas
    normalized = []
    errors = 0
    for rp in rows:
        try:
            normalized.append(connector.normalize(rp))
        except Exception:
            errors += 1

    values = [float(n["current_value"]) for n in normalized if n["current_value"]]
    discounts = [float(n["discount_percent"]) for n in normalized if n["discount_percent"]]
    types = {}
    for n in normalized:
        types[n["property_type"]] = types.get(n["property_type"], 0) + 1

    print(f"\n=== Estatísticas ({UF}) ===")
    print(f"  Total parseados : {len(rows)}")
    print(f"  Normalizados OK : {len(normalized)}")
    print(f"  Erros           : {errors}")
    if values:
        print(f"  Preço mín/máx   : R$ {min(values):,.0f} / R$ {max(values):,.0f}")
        print(f"  Desconto médio  : {sum(discounts)/len(discounts):.1f}%" if discounts else "  Desconto       : n/d")
    for tp, cnt in sorted(types.items(), key=lambda x: -x[1])[:5]:
        print(f"  {tp:<30} {cnt}")


if __name__ == "__main__":
    main()
