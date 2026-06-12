# Análise de Concorrência — Radar Imóvel

> Pesquisa de mercado realizada em 2026-06-11 (busca web). Objetivo: mapear o que os
> concorrentes oferecem hoje e onde o Radar Imóvel pode se diferenciar (céu azul).

---

## 1. Mapa do mercado

O mercado brasileiro de "imóveis de leilão/venda de bancos" tem 4 categorias de players.
**Nossos concorrentes diretos são as categorias A e B** (agregadores e plataformas com IA).
As categorias C e D são canais de venda e serviços — potenciais **parceiros**, não rivais.

### A. Agregadores/buscadores com alertas (concorrência direta)

| Player | O que oferece | Preço | Pontos fortes | Pontos fracos |
|--------|--------------|-------|---------------|---------------|
| **Leilão Imóvel** (leilaoimovel.com.br) | Busca em 800+ leiloeiros e bancos, atualização diária, alertas, "aprovação de financiamento em 24h" | Gratuito (monetiza com lead de financiamento) | Maior audiência/SEO da categoria; marca forte | Sem análise profunda; atualização apenas diária; sem score de risco |
| **Núcleo Leilões** (nucleoleiloes.com.br) | +60.000 imóveis, 800 leiloeiros, filtros + geolocalização (raio 150km), export Excel, comparativo com mercado convencional, parecer jurídico avulso | Freemium (gratuito com volume reduzido) | Maior base declarada; comparativo de mercado | IA superficial; parecer jurídico é serviço manual avulso |
| **Monitor Leilão** (monitorleilao.com.br) | Plataforma de busca judicial/extrajudicial, calculadora do investidor, pesquisa visual no Google Maps, alertas por e-mail + **assessoria** e **desocupação** como serviços | Freemium; planos mensal/trimestral/anual; garantia 7 dias | Ecossistema completo (plataforma + assessoria + desocupação); ~10 anos de mercado | Alertas só por e-mail diário; sem IA; foco em leilão judicial |
| **Auket** (auket.com.br) | 20+ filtros, mapa interativo, análise financeira (ROI, TIR, Payback, Cap Rate), simulação venda/aluguel, Kanban de carteira, análise jurídica centralizada, relatórios compartilháveis, alertas e-mail/WhatsApp, gestão colaborativa | Solo R$ 89,90/mês; Plus R$ 179,90/mês (grupos/assessorias) | Melhor ferramenta financeira da categoria; recurso colaborativo | Sem IA explícita; sem score de risco; sem foco em bancos públicos |

### B. Plataformas com IA (concorrência direta — a fronteira atual)

| Player | O que oferece | Preço | Pontos fortes | Pontos fracos |
|--------|--------------|-------|---------------|---------------|
| **Smart Leilões** (smartleiloes.app) | 34.500+ imóveis de 97 leiloeiros + Caixa; **IA avalia matrícula + edital e gera ranking 0–100**; calculadora de custos/ROI com tabelas de cartório de 27 estados; Kanban do leilão à revenda; divisão de cotas com parceiros; alertas e-mail/push/**WhatsApp**; extensão Chrome | Freemium (grátis = Caixa + calculadora + gerenciador; Premium pago) | Concorrente mais parecido com a nossa visão; ecossistema com curso/comunidade | Cobertura de bancos públicos limitada (só Caixa); ranking IA é caixa-preta; sem risco geoespacial |
| **Arremata.ai** | IA extrai dados de **matrícula em PDF**, notificações inteligentes, análise de mercado com IA, calculadora de ganhos; coleta de fontes oficiais | Freemium → plano GOLD (inclui curso de arrematação) | Análise de matrícula com IA bem resolvida | Escopo restrito à análise documental; sem pipeline de monitoramento amplo |
| **Leilão Ninja** / **BUSCAi Leilões** | Busca de imóveis de leilão "com IA" e análise inteligente | n/d | — | Players menores, proposta pouco diferenciada |

### C. Canais de venda (não concorrem — são fontes ou parceiros)

- **Resale** (adquirida pelo BTG Pactual): plataforma B2B que ajuda **bancos** a precificar e
  escoar imóveis retomados (IA de pricing do lado do vendedor). Dado interessante: **78% dos
  compradores via Resale nunca tinham comprado imóvel e rejeitam o modelo de leilão por
  acharem confuso** → confirma a tese de que existe um público enorme mal atendido que quer
  venda direta simplificada, não leilão.
- **Portal Zuk, Mega Leilões, Sodré Santoro etc.**: leiloeiros oficiais — são a *fonte* dos
  dados, não concorrentes.
- **Portais dos próprios bancos** (venda-imoveis.caixa.gov.br, portal BB, etc.): UX ruim,
  sem alertas, sem histórico — é exatamente a dor que motivou o Radar Imóvel.

### D. Educação + serviços

- Cursos de arrematação (Smart Leilões, Arremata.ai GOLD), assessoria e desocupação
  (Monitor Leilão / desocupacaoleiloes.com.br). Modelo de receita complementar comum no setor.

---

## 2. O que TODOS já têm (mesa de apostas mínima)

Para competir, é o básico esperado — não é diferencial:

1. Agregação multi-fonte com atualização **diária**
2. Filtros avançados + busca por mapa
3. Alertas de novos imóveis (e-mail; os melhores têm WhatsApp/push)
4. Calculadora de viabilidade (custos de cartório, ITBI, ROI)
5. Modelo freemium

## 3. O que SÓ os líderes têm (fronteira atual)

1. IA lendo **matrícula e edital** com ranking de oportunidade (Smart Leilões, Arremata.ai)
2. Gestão de carteira pós-arremate em Kanban (Smart Leilões, Auket)
3. Análise financeira sofisticada — TIR, Cap Rate, simulação aluguel (Auket)
4. Colaboração em grupo / divisão de cotas (Auket Plus, Smart Leilões)
5. Serviços de assessoria/desocupação integrados (Monitor Leilão)

---

## 4. Lacunas do mercado → onde o Radar Imóvel ganha

### 4.1 Diferenciais que JÁ TEMOS construídos (atacar no posicionamento)

| Diferencial | Estado | Por que ninguém tem |
|-------------|--------|---------------------|
| **Cobertura total de bancos públicos** (Caixa, BB, BRB, BNB, BASA, Banrisul, Banestes) | ✅ 7 connectors shipped (Fase 3) | Todos focam em leiloeiros + Caixa; BNB/BASA/Banrisul/Banestes são invisíveis para o mercado — imóveis com menos disputa |
| **Velocidade event-driven** — detecção de mudança de preço/status via Pub/Sub, não crawl diário | ✅ Arquitetura pronta | Concorrentes atualizam 1×/dia; alertar **horas antes** muda o jogo em venda direta (ordem de chegada de proposta) |
| **Score de Risco multidimensional 0–100** cruzando CNJ, IBGE, CEMADEN, ICMBio, FUNAI, IPEA, Receita — risco **fundiário, ambiental, climático e socioeconômico** | ✅ Shipped (2026-06-10) + geodados (2026-06-11) | A "IA" dos concorrentes lê documento; **ninguém cruza geodado público** (área de risco CEMADEN, terra indígena FUNAI, unidade de conservação ICMBio) |
| **Histórico de mudanças de preço por imóvel** (`property_changes`) | ✅ No schema desde a Fase 1 | Nenhum concorrente mostra a curva de desconto do imóvel ao longo do tempo |
| **Relatório PDF de due diligence** automatizado | ✅ Shipped no Mapa de Risco | Núcleo Leilões cobra parecer jurídico manual avulso |
| **Alerta Telegram** nativo | ✅ Fase 1 | Maioria usa e-mail; só os top têm WhatsApp |

### 4.2 Posicionamento sugerido

> **"O Bloomberg dos imóveis de bancos públicos"** — não somos mais um buscador de leilão:
> somos inteligência de risco e velocidade para venda direta e licitação de bancos públicos,
> o segmento que os agregadores de leiloeiros ignoram.

Três mensagens-chave:
1. **Cobertura que ninguém tem** — 7 bancos públicos, incluindo regionais (BNB, BASA, Banrisul, Banestes) = oportunidades com menos concorrência de arrematantes.
2. **Velocidade** — alerta em near real-time vs. e-mail diário da concorrência.
3. **Risco de verdade** — não é "ranking de oportunidade" caixa-preta; é score explicável por dimensão (jurídico, fundiário/ambiental, climático, socioeconômico) com fonte pública citada.

---

## 5. Céu Azul — apostas de diferenciação (ninguém faz hoje)

Ordenadas por relação impacto × esforço, dado o que já temos:

### Curto prazo (alavanca o que está pronto)

1. **Curva de desconto preditiva** 📉 — a Caixa rebaixa preço em etapas previsíveis
   (1º leilão → 2º leilão → venda direta com desconto progressivo). Com o `property_changes`
   + ML simples, prever: *"este imóvel tem 73% de chance de cair mais 10% em 30 dias"*.
   Vira decisão de comprar agora vs. esperar — **nenhum player tem isso** e nós já coletamos
   a série histórica.
2. **"Pergunte ao edital"** 💬 — chat RAG sobre o edital/matrícula do imóvel (Vertex AI
   Vector Search, já planejado na stack). Concorrentes extraem campos; nós deixamos o usuário
   *conversar* com o documento: "posso financiar?", "tem dívida de condomínio?", "quem paga o ITBI?".
3. **Radar Index** 📊 — índice público mensal de deságio por região/banco (mediana
   avaliação vs. preço de venda). Conteúdo de PR/SEO que gera autoridade e backlinks —
   estratégia que nenhum concorrente faz com dado proprietário.
4. **Alerta "segundos depois"** ⚡ — SLA público de latência de alerta (ex.: novo imóvel
   notificado em < 15 min). Transformar a arquitetura event-driven em promessa de marketing
   mensurável.

### Médio prazo

5. **Score de revenda por m² hiperlocal** — cruzar preço do leilão com anúncios de mercado
   (Fase 4 já prevista) + tempo médio de venda no bairro → "lucro provável e em quanto tempo".
   Auket calcula TIR com inputs manuais; nós preenchemos os inputs automaticamente.
6. **API B2B / data feed** 🏦 — vender o dado normalizado + score de risco para fundos
   imobiliários, family offices, assessorias e fintechs de crédito. Os concorrentes são
   B2C-only; o ativo (pipeline de 7 bancos + risco geoespacial) vale mais no atacado.
7. **Modo "primeira compra"** 🧭 — a Resale provou que 78% dos compradores rejeitam leilão
   por confusão. Uma jornada guiada passo a passo (checklist do edital ao registro, com a IA
   explicando cada etapa do imóvel específico) captura o público iniciante que os sites de
   "investidor profissional" afugentam.
8. **Marketplace de serviços** — conectar arrematante a advogado/despachante/desocupação
   por comissão (modelo Monitor Leilão, mas como marketplace aberto e ranqueado, não serviço próprio).

### Longo prazo / visão

9. **Gêmeo financeiro do imóvel** — para cada imóvel, um dossiê vivo: risco, curva de preço,
   simulação de financiamento real (taxas Caixa atuais), custo total até a escritura,
   probabilidade de desocupação litigiosa (dado CNJ por comarca).
10. **Expansão para leilões judiciais** com o mesmo motor de risco — TAM muito maior, e o
    score fundiário/ambiental se torna ainda mais valioso (riscos jurídicos maiores).
11. **Crédito embutido** — parceria/originação de financiamento para arremate (modelo de
    monetização do Leilão Imóvel, mas com nosso score de risco como underwriting).

---

## 6. Tabela de preços dos concorrentes (pesquisa 2026-06-11)

### Núcleo Leilões (preços públicos, planos anuais parcelados em 12×)

| Plano | Preço | Inclui |
|-------|-------|--------|
| Gratuito | R$ 0 | Volume reduzido de imóveis |
| **Plus Anual** | **R$ 63,92/mês** (R$ 767,04/ano) | +70.000 imóveis, 900 leiloeiros, robô de alertas |
| **Premium Anual** | **R$ 103,92/mês** (R$ 1.247,04/ano) | + alerta WhatsApp, calculadora de custos, export Excel, 1 parecer jurídico/ano, comparativo de mercado |
| **Master Anual** | **R$ 187,49/mês** (R$ 2.249,90/ano) | + leilão negativo, 12 pareceres/ano, 50% off em pareceres extras, reunião mensal com advogado |
| Assessoria "Investidor" | R$ 824,91/mês (R$ 9.899/ano) | Assessoria completa de 1 arrematação/ano, imissão na posse, transferência de matrícula |
| Parecer jurídico avulso | R$ 619 (1×) · R$ 1.099 (2×) · R$ 1.399 (3×) | 30 min com advogado + análise de dívidas, processos, penhoras, matrícula e edital |

### Auket (preços públicos)

| Plano | Mensal | Anual (equiv./mês) | Inclui |
|-------|--------|--------------------|--------|
| **Solo** | **R$ 89,90** | R$ 75,90 | Investidor individual: filtros, mapa, análise financeira, Kanban, alertas |
| **Plus** | **R$ 179,90** | R$ 149,90 | + gestão colaborativa, compartilhamento por perfil (grupos/assessorias) |

Ambos com 7 dias de teste grátis.

### Demais players (preço não divulgado publicamente — atrás de login/checkout)

| Player | Modelo confirmado | Observação |
|--------|-------------------|------------|
| **Smart Leilões** | Freemium → Premium pago | Grátis: imóveis Caixa + calculadora + gerenciador. Preço do Premium só após cadastro |
| **Monitor Leilão** | Freemium → mensal/trimestral/anual | Vendido via Hotmart; garantia incondicional de 7 dias; "planos mais longos têm desconto" |
| **Arremata.ai** | Freemium → GOLD (inclui curso de arrematação) | Site anuncia "economize R$ 220/ano" no anual; garantia de 30 dias |
| **Leilão Imóvel** | Gratuito para o comprador | Monetiza com lead de financiamento ("aprovação em 24h") e anúncios |
| **Leilão Rápido** | Assinatura mensal única + trial 7 dias | Alertas em tempo real como proposta central — valor não público |

### Leitura estratégica do preço

- **Faixa B2C consolidada: R$ 60–190/mês** (anual entre R$ 750 e R$ 2.250). É o teto psicológico do investidor pessoa física.
- **Padrão da categoria:** freemium agressivo + trial 7 dias + desconto forte no anual (~20–30%).
- **Serviço jurídico é o upsell de maior ticket** (parecer avulso a R$ 619+; assessoria a R$ 9.899/ano) — o nosso relatório de due diligence **automatizado** ataca exatamente essa linha de receita com custo marginal ~zero.
- **Espaço de entrada sugerido para o Radar:** gratuito (busca + alerta diário) → ~R$ 49–79/mês (tempo real + score de risco + due diligence PDF) → ~R$ 149–199/mês (curva preditiva + API/export + colaboração). Entramos abaixo do Premium do Núcleo com mais valor entregue, e o tier alto compete com Auket Plus/Master.

---

## 7. Modelo de monetização — referências do mercado

| Modelo | Quem usa | Aplicável ao Radar? |
|--------|----------|---------------------|
| Freemium + assinatura (R$ 75–180/mês) | Auket, Smart Leilões, Núcleo, Monitor | ✅ Caminho principal B2C: grátis = busca + alerta diário; pago = tempo real, score de risco, due diligence PDF, curva preditiva |
| Lead de financiamento | Leilão Imóvel | ✅ Complementar (sem custo para o usuário) |
| Curso/comunidade | Smart Leilões, Arremata.ai | ⚠️ Possível, mas desvia do produto |
| Serviços (assessoria/desocupação) | Monitor Leilão | ✅ Via marketplace (comissão), não operação própria |
| Dados B2B / API | ninguém (só a Resale, do lado do vendedor) | 🌟 Céu azul — diferencial estrutural |

---

## Fontes

- https://smartleiloes.app/ · https://www.smartleiloes.com.br/
- https://www.monitorleilao.com.br/ · https://assessoria.monitorleilao.com.br/
- https://nucleoleiloes.com.br/
- https://www.auket.com.br/
- https://www.leilaoimovel.com.br/
- https://arremata.ai/ · https://leilaoninja.com/ · https://buscaileiloes.com.br/
- https://www.portalzuk.com.br/
- https://www.projetodraft.com/recem-adquirida-pelo-btg-pactual-a-resale-simplifica-a-compra-e-venda-de-imoveis-retomados-por-inadimplencia/
- https://venda-imoveis.caixa.gov.br/ · https://www.bb.com.br/site/compras-contratacao-e-venda-de-imoveis/
