# SHIP: MVP Fase 1 — Radar Imóvel (Caixa)

| Attribute | Value |
|-----------|-------|
| **Feature** | MVP_FASE1_CAIXA |
| **BUILD_REPORT** | `.claude/sdd/reports/BUILD_REPORT_FASE1_MVP_CAIXA.md` |
| **Shipped** | 2026-06-08 |
| **Status** | ✅ SHIPPED |

---

## O que foi entregue

Plataforma completa de monitoramento de leilões da Caixa Econômica Federal:

- **Coleta automatizada** de imóveis por UF (27 fontes) com Playwright anti-detecção para bypass do Radware Bot Manager
- **Scraping de detalhe** por imóvel: CEP, foto, áreas, URL do edital
- **Pipeline de processamento:** deduplicação SHA-256, detecção de mudanças de preço/status, score básico (desconto + ocupação)
- **Alertas Telegram** personalizados por watchlist (UF, cidade, preço, desconto)
- **API FastAPI** no Cloud Run com Firebase Auth JWT
- **Dashboard Next.js** com tabela, filtros, detalhe, alertas, configurações e admin
- **Infra GCP** completa via Terraform (Cloud SQL, Cloud Run, Pub/Sub, Cloud Scheduler, Secret Manager, IAM)
- **CI/CD** via Cloud Build + GitHub Actions (Workload Identity)

---

## Métricas finais

| Métrica | Valor |
|---------|-------|
| Arquivos de código entregues | 74 + ~15 extras (desvios planejados) |
| Migrations Alembic | 003 (001 schema + 002 + 003 seed banks) |
| Commits totais da fase | ~35 (initial + hardening) |
| Testes (unit + integration) | ✅ Pass |
| Deploy Cloud Run | ✅ API + Job + Frontend |

---

## Lições aprendidas

### O que funcionou bem

1. **SDD antes do código** — ter BRAINSTORM → DEFINE → DESIGN prontos antes do initial commit acelerou radicalmente a execução; cada arquivo do manifesto tinha propósito claro.
2. **`DRY_RUN=true`** no job de coleta — permite validar parsing sem poluir o banco; adotado desde o início e usado em todos os validadores.
3. **Settings opcionais para dependências externas** — tornar `PUBSUB_*`, `TELEGRAM_*`, `FIREBASE_*` opcionais em `Settings` eliminou a necessidade de credenciais completas em dev local e simplificou smoke tests.
4. **Deduplicação por content_hash SHA-256** — simples e eficaz; não depende de unicidade do `external_code` (que pode mudar no site da Caixa).

### O que custou tempo

1. **Radware Bot Manager** — não estava previsto no DESIGN. O site da Caixa bloqueia httpx/requests. Solução: Playwright com anti-detecção. Custo: ~1 dia de investigação + implementação.
2. **Cloud SQL connector no Cloud Run** — o DESIGN previa URL de conexão direta; no Cloud Run é obrigatório o `cloud-sql-python-connector` com `pg8000`. Causou falha no primeiro deploy.
3. **Firebase Hosting vs Cloud Run para o frontend** — static export do Next.js com rotas dinâmicas (`/imoveis/[id]`) não funciona bem no Firebase Hosting sem configuração adicional. Migrar para Cloud Run + nginx foi a solução mais limpa, mas não estava no DESIGN.
4. **Tailwind/PostCSS** — config não estava nos arquivos do manifesto; ausência fez o CSS não ser processado e o layout aparecer sem estilo.

### Surpresas positivas

- **Parser CSV da Caixa** adaptou-se ao formato real mais rápido que o esperado (o DESIGN previa XLSX como formato primário, mas o site usa CSV).
- **`validate_caixa.py`** (script extra, não no manifesto) foi essencial para validar a coleta real antes de qualquer commit — prática a adotar em todas as fases.

---

## Dívida técnica conhecida

| Item | Prioridade | Descrição |
|------|-----------|-----------|
| `test_api_properties.py` | Média | Requer o extra `api` (FastAPI) instalado; não roda no venv padrão `job` |
| `secret_manager.tf` | Baixa | Sintaxe `replication { auto {} }` pode causar `terraform validate` error dependendo da versão do provider |
| Playwright headful fallback | Média | Sem retry exponencial em caso de CAPTCHA rotativo |
| Geocoding | Baixa | `geocoding.py` usa ViaCEP + Nominatim; sem cache Redis = lento em coletas grandes |

---

## Próximas fases construídas sobre esta base

- **Fase 2** (IA nos editais): `eb6a606` — leitura de editais com Gemini + score enriquecido
- **Fase 3** (todos os bancos): `cb5b9a2` — connectors BB, BRB, BNB, BASA, Banrisul, Banestes

---

## Arquivos arquivados

Todos os artefatos SDD da Fase 1 permanecem em `.claude/sdd/features/`:
- `BRAINSTORM_MVP_FASE1_CAIXA.md`
- `DEFINE_MVP_FASE1_CAIXA.md`
- `DESIGN_MVP_FASE1_CAIXA.md` (status atualizado para `Built / Complete`)
- `BUILD_REPORT_FASE1_MVP_CAIXA.md` (este relatório)
