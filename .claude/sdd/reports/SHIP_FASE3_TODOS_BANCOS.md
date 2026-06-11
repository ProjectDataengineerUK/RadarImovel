# SHIP: Fase 3 — Todos os Bancos Públicos

| Attribute | Value |
|-----------|-------|
| **Feature** | FASE3_TODOS_BANCOS |
| **BUILD_REPORT** | `.claude/sdd/reports/BUILD_REPORT_FASE3_TODOS_BANCOS.md` |
| **Shipped** | 2026-06-08 |
| **Commit** | `cb5b9a2` |
| **Status** | ✅ SHIPPED |

---

## O que foi entregue

Expansão do sistema para todos os 7 bancos públicos brasileiros monitorados:

- **6 connectors novos** (BB, BRB, BNB, BASA, Banrisul, Banestes) — cada um com `__init__`, `collector`, `parser`, `normalizer` seguindo a interface `BankConnector`
- **`CONNECTOR_REGISTRY`** — resolução dinâmica de connector por `bank_code`; `get_connector("itau")` → `ValueError`
- **`normalize_utils.py`** e **`pdf_utils.py`** — helpers compartilhados (`parse_decimal_br`, `parse_occupancy`, `parse_br_date`, `extract_tables`, etc.) que eliminaram duplicação entre connectors
- **`jobs/collect_bank.py`** — job genérico que substitui `collect_caixa.py` como implementação real; `collect_caixa.py` virou thin-shim retrocompatível
- **`DRY_RUN=true`** — modo dry run no job genérico; sem GCS, sem DB, sem Pub/Sub
- **Migration `005_update_banks.py`** — coluna `scraping_strategy` na tabela `banks`; mantém somente Caixa `active=true` por padrão
- **Infra Terraform** — job `radar-collect-bank` genérico + schedulers por banco via `setproduct`
- **44 testes novos** (unit por banco + registry + normalize_utils)

---

## Métricas finais

| Métrica | Valor |
|---------|-------|
| Connectors novos | 6 |
| Arquivos criados | 32 |
| Arquivos modificados | 7 |
| Unit tests da fase | 44/44 pass |
| Unit tests totais | 94/94 pass |
| Lint (ruff) | ✅ Pass |
| Types (mypy, arquivos da fase) | ✅ Pass |

---

## Lições aprendidas

### O que funcionou bem

1. **`normalize_utils.py` centralizado** — refatorar o normalizer da Caixa para importar helpers antes de escrever os novos connectors evitou copy-paste e garantiu consistência de parsing decimal/BR em todos os bancos.
2. **`pdf_utils.py` como extra** — não estava no manifesto mas surgiu naturalmente ao implementar BNB/BASA/Banestes; os 3 bancos compartilham exatamente as mesmas operações pdfplumber.
3. **Data Quality Gate `job.zero_properties`** — logar quando 0 imóveis são extraídos é o sinal mais valioso para detectar mudança de layout sem depender de monitoramento ativo.
4. **`bank.active=false` como circuit breaker** — bancos com layout ainda não validado ficam desabilitados por padrão; ativar é uma linha de SQL, não um redeploy.

### O que custou tempo

1. **Instalação de `pdfplumber`** — o `.venv` do repo não tinha `pip` bootstrap; foi necessário `ensurepip` antes de instalar `pdfplumber`. Em produção (Docker), `pyproject.toml` garante a dependência; em dev local, documentar o bootstrap.
2. **Estrutura HTML/PDF hipotética** — as URLs e seletores de cada banco são estimativas baseadas em documentação pública e padrões conhecidos; nenhum foi validado contra o site real. Isso é intencional (fase de código), mas requer sprint de validação antes de ativar qualquer banco.
3. **`fastapi` ausente no venv** — `test_api_properties.py` não coletou durante os testes da fase por gap pré-existente (o extra `api` não estava instalado no venv de dev). Não é regressão da Fase 3.

### Surpresas positivas

- **`discover_sources()` offline** retornou contagens corretas para todos os bancos sem chamadas HTTP (caixa: 27, bb: 2, brb: 2, bnb: 1, banrisul: 1), confirmando que o registry e as fontes estão corretamente configurados.
- **Retrocompatibilidade total** — `collect_caixa.py` como thin-shim não quebrou nenhum scheduler ou job existente.

---

## Dívida técnica conhecida

| Item | Prioridade | Descrição |
|------|-----------|-----------|
| Validação de URLs/layouts reais | Crítica | Todos os 6 connectors novos têm URLs e seletores **hipotéticos** — precisam ser validados banco a banco com snapshots HTML/PDF reais |
| `test_api_properties.py` | Média | Extra `api` ausente no venv de dev; instalar `pip install -e ".[api]"` para rodar |
| Playwright para BB | Média | Fallback está implementado mas não testado com resposta real; BB pode ter proteção anti-bot |
| `pdfplumber` bootstrap em dev | Baixa | Documentar que `python -m ensurepip && pip install -e ".[job]"` é necessário em venv fresh |

---

## Ordem recomendada de validação em produção

1. **BB** — portal mais estável, HTML cards, menor risco
2. **Banrisul** — HTML simples, lançado em abril/2026
3. **BNB** — HTML + PDF de relação, dois caminhos a validar
4. **BRB** — HTML oficial + JSON Resale, `source_name` distinto
5. **BASA** — índice HTML → PDF edital, maior complexidade
6. **Banestes** — publicações legais em PDF, menor volume

Para cada banco: salvar snapshot real → atualizar fixtures + seletores → `UPDATE banks SET active=true WHERE code='<banco>'` → adicionar a `var.enabled_banks` no Terraform.

---

## Arquivos arquivados

- `BRAINSTORM_FASE3_TODOS_BANCOS.md`
- `DEFINE_FASE3_TODOS_BANCOS.md`
- `DESIGN_FASE3_TODOS_BANCOS.md` (status atualizado para `Built / Complete`)
- `BUILD_REPORT_FASE3_TODOS_BANCOS.md`
