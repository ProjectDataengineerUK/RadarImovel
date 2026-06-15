# BUILD REPORT: Fase 3 — Todos os Bancos Públicos

> Implementação dos connectors para todos os bancos públicos brasileiros (BB, BRB,
> BNB, BASA, Banrisul, Banestes), job genérico `collect_bank.py`, registry,
> utilitários compartilhados, migration, Terraform e testes.

| Atributo | Valor |
|----------|-------|
| **Feature** | FASE3_TODOS_BANCOS |
| **DESIGN** | `.claude/sdd/features/DESIGN_FASE3_TODOS_BANCOS.md` |
| **Data** | 2026-06-08 |
| **Status** | ✅ COMPLETE |

---

## Summary

| Métrica | Valor |
|---------|-------|
| Connectors novos | 6 (bb, brb, bnb, basa, banrisul, banestes) |
| Arquivos criados | 32 |
| Arquivos modificados | 7 |
| Testes novos | 8 arquivos / 44 testes |
| Unit tests totais | 94 passando |
| Lint (ruff) | ✅ Pass (arquivos da fase) |
| Types (mypy) | ✅ Pass (arquivos da fase) |

> Observação de ambiente: o virtualenv `.venv` não tinha `pip`, `pdfplumber` nem
> `reportlab`. `pip` foi bootstrapado via `ensurepip`; `pdfplumber` (dependência
> real adicionada ao extra `job`) e `reportlab` (apenas para gerar fixtures PDF)
> foram instalados. `fastapi` continua ausente no venv (gap pré-existente,
> não relacionado a esta fase) — por isso `tests/integration/test_api_properties.py`
> não coleta; os demais testes rodam normalmente.

---

## Tasks com Atribuição

### 1. Utilitários compartilhados

| Arquivo | Ação | Status | Notas |
|---------|------|--------|-------|
| `app/connectors/normalize_utils.py` | Create | ✅ | `parse_decimal_br`, `parse_discount_br`, `parse_occupancy`, `clean_text`, `extract_type`, `parse_br_date`, `compute_discount` |
| `app/connectors/pdf_utils.py` | Create | ✅ | Helper extra (não no manifesto): `extract_tables`, `extract_text`, `rows_from_tables`, `is_pdf` — reuso BNB/BASA/Banestes |
| `app/connectors/__init__.py` | Modify | ✅ | `CONNECTOR_REGISTRY` + `get_connector(bank_code, **kwargs)` |
| `app/connectors/caixa/normalizer.py` | Modify | ✅ | Refatorado para importar helpers de `normalize_utils` (retrocompatível; testes Caixa seguem passando) |

### 2–7. Connectors por banco (4 arquivos cada)

| Banco | `__init__` | `collector` | `parser` | `normalizer` | Estratégia |
|-------|-----------|-------------|----------|--------------|-----------|
| **bb** | ✅ | ✅ | ✅ | ✅ | httpx + fallback Playwright; BS4 sobre cards; nacional |
| **brb** | ✅ | ✅ | ✅ | ✅ | httpx; detecta HTML oficial vs JSON Resale; `source_name` distinto |
| **bnb** | ✅ | ✅ | ✅ | ✅ | httpx; HTML (tabela) **ou** PDF de relação (pdfplumber) |
| **basa** | ✅ | ✅ | ✅ | ✅ | httpx; índice HTML → links PDF; edital PDF (pdfplumber) com `edital_number`/`auction_date` |
| **banrisul** | ✅ | ✅ | ✅ | ✅ | httpx; BS4 cards; default state RS |
| **banestes** | ✅ | ✅ | ✅ | ✅ | httpx; índice HTML → PDF edital (pdfplumber); default state ES |

### 8. Job genérico

| Arquivo | Ação | Status | Notas |
|---------|------|--------|-------|
| `jobs/collect_bank.py` | Create | ✅ | Lê `BANK` env, resolve via registry, checa `bank.active`, suporta `DRY_RUN`, `UF` opcional, detail_scraper só para caixa; mantém upload GCS, dedup, change detection, publish |
| `jobs/collect_caixa.py` | Modify | ✅ | Convertido em thin-shim retrocompatível (`BANK=caixa` → `collect_bank.run`) |

### 9. Migration

| Arquivo | Ação | Status | Notas |
|---------|------|--------|-------|
| `migrations/versions/005_update_banks.py` | Create | ✅ | Adiciona coluna `scraping_strategy` em `banks`; preenche estratégia por banco; mantém apenas Caixa `active=true` por padrão |
| `app/models/bank.py` | Modify | ✅ | Campo `scraping_strategy: str \| None` no model (sync com migration) |

### 10. Terraform

| Arquivo | Ação | Status | Notas |
|---------|------|--------|-------|
| `infra/terraform/cloud_run.tf` | Modify | ✅ | Job genérico `radar-collect-bank` (`python -m jobs.collect_bank`, env `BANK` default vazio) |
| `infra/terraform/scheduler.tf` | Modify | ✅ | Schedulers por banco via `setproduct(var.enabled_banks − caixa, schedules)` |
| `infra/terraform/variables.tf` | Modify | ✅ | `enabled_banks` (default `["caixa"]`), `bank_request_delay_ms` |

### 11. Testes e fixtures

| Arquivo | Ação | Status |
|---------|------|--------|
| `tests/fixtures/html/bb_list.html` | Create | ✅ |
| `tests/fixtures/html/brb_list.html` + `brb_resale.json` | Create | ✅ |
| `tests/fixtures/html/bnb_list.html` + `bnb_relacao.pdf` | Create | ✅ |
| `tests/fixtures/html/basa_edital.pdf` | Create | ✅ |
| `tests/fixtures/html/banrisul_list.html` | Create | ✅ |
| `tests/fixtures/html/banestes_edital.pdf` | Create | ✅ |
| `tests/unit/connectors/test_normalize_utils.py` | Create | ✅ (13 testes) |
| `tests/unit/connectors/test_bb_parser.py` | Create | ✅ (5) |
| `tests/unit/connectors/test_brb_parser.py` | Create | ✅ (4) |
| `tests/unit/connectors/test_bnb_parser.py` | Create | ✅ (3) |
| `tests/unit/connectors/test_basa_parser.py` | Create | ✅ (3) |
| `tests/unit/connectors/test_banrisul_parser.py` | Create | ✅ (3) |
| `tests/unit/connectors/test_banestes_parser.py` | Create | ✅ (3) |
| `tests/unit/connectors/test_registry.py` | Create | ✅ (10) |

### 12. Dependências

| Arquivo | Ação | Status | Notas |
|---------|------|--------|-------|
| `pyproject.toml` | Modify | ✅ | `pdfplumber>=0.11` adicionado ao extra `job` |

---

## Verificação

| Check | Resultado |
|-------|-----------|
| Lint (ruff) nos arquivos da fase | ✅ Pass |
| Types (mypy) nos connectors/utils | ✅ Pass (erros remanescentes são pré-existentes: relationships forward-ref, `google.cloud.*` stubs, detail_scraper) |
| Unit tests da fase | ✅ 44/44 pass |
| Unit tests totais | ✅ 94/94 pass |
| Registry resolve 7 bancos | ✅ |
| `get_connector("itau")` → ValueError | ✅ |
| Import `jobs.collect_bank` | ✅ |
| `discover_sources()` (offline) | ✅ caixa 27, bb 2, brb 2, bnb 1, banrisul 1 |
| PDF extraction (pdfplumber) | ✅ 3 linhas por fixture (bnb/basa/banestes) |
| Terraform fmt (arquivos da fase) | ✅ well-formed |

---

## Robustez implementada

- **Defensividade por campo:** todos os parsers isolam cada campo; ausência gera
  `logger.warning` e segue como `None`. Nenhum crash por campo faltando.
- **`fetch_raw` detecta challenge/CAPTCHA:** verifica `<html`/`captcha`/`challenge`
  onde se espera CSV/PDF e retorna `b""`; BB cai para Playwright como fallback.
- **`DRY_RUN=true`:** `collect_bank` busca e parseia mas não persiste (sem GCS,
  sem DB, sem publish).
- **Detecção de content-type:** BNB/BASA/Banestes distinguem PDF (`%PDF`) de HTML.
- **Data Quality Gate:** `collect_bank` loga `job.zero_properties` quando 0 imóveis
  são extraídos (sinal de mudança de layout).
- **`bank.active=false`:** job loga `job.bank_inactive` e encerra sem coletar.

---

## Notas para validação em produção (próximo passo)

As URLs e estruturas HTML/PDF de cada banco são **hipóteses** isoladas em
constantes no topo de cada `collector.py`/`parser.py`. Recomendação:

1. Validar um banco por vez (ordem sugerida pelo DESIGN: BB → Banrisul → BNB →
   BRB → BASA → Banestes).
2. Salvar um snapshot HTML/PDF real e atualizar os fixtures + seletores
   (`_CARD_SELECTORS`, `_FIELD_SELECTORS`, `_COLUMN_ALIASES`).
3. Habilitar o banco com `UPDATE banks SET active=true WHERE code='<banco>'` e
   adicioná-lo a `var.enabled_banks` no Terraform.

## Status: ✅ COMPLETE
