"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

const BANKS = [
  { name: "Caixa", tag: "CEF" },
  { name: "Banco do Brasil", tag: "BB" },
  { name: "BRB", tag: "BRB" },
  { name: "Banco do Nordeste", tag: "BNB" },
  { name: "Banco da Amazônia", tag: "BASA" },
  { name: "Banrisul", tag: "RS" },
  { name: "Banestes", tag: "ES" },
];

const AUCTIONEERS = [
  { name: "Fidalgo", tag: "Leiloeiro" },
  { name: "Frazão", tag: "Leiloeiro" },
  { name: "Sodré", tag: "Leiloeiro" },
  { name: "Lance Certo", tag: "Portal" },
  { name: "Superleilões", tag: "Portal" },
];

const JUDICIAL = [
  { name: "DataJud / CNJ", tag: "Federal" },
  { name: "TJSP", tag: "Estadual" },
  { name: "TRT 2ª", tag: "Trabalhista" },
  { name: "TRT 15ª", tag: "Trabalhista" },
];

const FEATURES = [
  {
    icon: "⚡",
    title: "Alertas antes do mercado",
    desc: "Notificações por Telegram em menos de 1 minuto quando um imóvel novo aparece ou o preço cai.",
  },
  {
    icon: "🎯",
    title: "Score de oportunidade",
    desc: "Pontuação 0–100 baseada em desconto sobre avaliação, situação de ocupação, pagamento e risco.",
  },
  {
    icon: "🤖",
    title: "Leitura de editais com IA",
    desc: "Gemini lê o edital e extrai ônus reais, dívidas de IPTU/condomínio, ocupação e data da hasta.",
  },
  {
    icon: "🔍",
    title: "Detector de 2ª Praça",
    desc: "Identifica automaticamente imóveis com queda ≥ 40% — as maiores oportunidades do leilão.",
  },
  {
    icon: "🧮",
    title: "Calculadora de ROI",
    desc: "Simule entrada, ITBI, reforma, financiamento e valor de revenda. Resultado em segundos.",
  },
  {
    icon: "🛡️",
    title: "Mapa de Risco multidimensional",
    desc: "6 dimensões: jurídico, fundiário, fiscal, ocupação, socioeconômico e mercado. Score 0–100.",
  },
  {
    icon: "📈",
    title: "Comparação FipeZap",
    desc: "Veja o desconto do imóvel em relação ao preço de mercado do bairro — dados FipeZap integrados.",
  },
  {
    icon: "🗺️",
    title: "Radar Index por município",
    desc: "Inteligência de mercado por cidade: volume de leilões, desconto médio e tendência de preço.",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Crie sua conta grátis",
    desc: "Login com Google em segundos. Plano gratuito disponível sem cartão de crédito.",
  },
  {
    step: "02",
    title: "Configure seus alertas",
    desc: "Escolha estado, tipo de imóvel (casa, apto, comercial), faixa de preço e canal de notificação.",
  },
  {
    step: "03",
    title: "Analise e decida rápido",
    desc: "Score, edital lido por IA, ROI calculado e mapa de risco — tudo em uma tela antes da hasta.",
  },
];

export default function HomePage() {
  const { user, loading } = useAuth();

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-gray-800/60 bg-gray-950/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-blue-500 text-xl font-bold">⚖</span>
            <span className="text-white font-bold text-lg tracking-tight">Mastavista</span>
          </div>

          <div className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <a href="#funcionalidades" className="hover:text-white transition-colors">Funcionalidades</a>
            <a href="#fontes" className="hover:text-white transition-colors">Fontes</a>
            <Link href="/planos" className="hover:text-white transition-colors">Planos</Link>
          </div>

          <div className="flex items-center gap-3">
            {!loading && (
              user ? (
                <Link
                  href="/dashboard"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition-colors"
                >
                  Ir para o painel →
                </Link>
              ) : (
                <>
                  <Link href="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
                    Entrar
                  </Link>
                  <Link
                    href="/login"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition-colors"
                  >
                    Começar grátis
                  </Link>
                </>
              )
            )}
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-24 pb-20 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(37,99,235,0.15),transparent)]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-sm text-blue-400 mb-8">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
            16 fontes monitoradas em tempo real
          </div>

          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-tight mb-6">
            Inteligência em{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-600">
              leilões imobiliários
            </span>
          </h1>

          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Monitore Caixa, BB, BRB e mais 13 fontes. Receba alertas antes do mercado,
            leia editais com IA e calcule o ROI em segundos.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/login"
              className="px-8 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-colors text-base shadow-lg shadow-blue-500/20"
            >
              Começar grátis →
            </Link>
            <Link
              href="/planos"
              className="px-8 py-3.5 bg-gray-800 hover:bg-gray-700 text-white font-semibold rounded-xl transition-colors text-base border border-gray-700"
            >
              Ver planos
            </Link>
          </div>

          <p className="text-sm text-gray-600 mt-5">Sem cartão de crédito · Plano gratuito disponível</p>
        </div>
      </section>

      {/* ── Stats ───────────────────────────────────────────────────── */}
      <section className="border-y border-gray-800/60 bg-gray-900/40 py-10 px-6">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { value: "16", label: "fontes monitoradas" },
            { value: "7", label: "bancos públicos" },
            { value: "3", label: "tribunais judiciais" },
            { value: "< 1 min", label: "tempo de alerta" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
              <div className="text-sm text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────────────── */}
      <section id="funcionalidades" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              Tudo que você precisa para decidir rápido
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              Do alerta à análise de risco — sem precisar abrir 10 abas.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-gray-900 border border-gray-800 rounded-2xl p-6 hover:border-gray-700 transition-colors"
              >
                <div className="text-2xl mb-3">{f.icon}</div>
                <h3 className="text-white font-semibold mb-2 text-sm leading-snug">{f.title}</h3>
                <p className="text-gray-500 text-xs leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Sources ─────────────────────────────────────────────────── */}
      <section id="fontes" className="py-20 px-6 bg-gray-900/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">16 fontes monitoradas</h2>
            <p className="text-gray-400">
              A maior cobertura de leilões imobiliários bancários e judiciais do Brasil.
            </p>
          </div>

          <div className="space-y-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-600 mb-4">
                Bancos públicos
              </p>
              <div className="flex flex-wrap gap-2">
                {BANKS.map((b) => (
                  <span
                    key={b.name}
                    className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
                  >
                    <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                      {b.tag}
                    </span>
                    {b.name}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-600 mb-4">
                Leiloeiros e portais
              </p>
              <div className="flex flex-wrap gap-2">
                {AUCTIONEERS.map((a) => (
                  <span
                    key={a.name}
                    className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
                  >
                    <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                      {a.tag}
                    </span>
                    {a.name}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-600 mb-4">
                Hastas judiciais
              </p>
              <div className="flex flex-wrap gap-2">
                {JUDICIAL.map((j) => (
                  <span
                    key={j.name}
                    className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
                  >
                    <span className="text-xs font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                      {j.tag}
                    </span>
                    {j.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">Como funciona</h2>
            <p className="text-gray-400">Em 3 passos, do cadastro ao arremate.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {STEPS.map((s) => (
              <div key={s.step} className="relative">
                <div className="text-5xl font-black text-gray-800 mb-4 font-mono">{s.step}</div>
                <h3 className="text-white font-semibold text-lg mb-2">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing teaser ──────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-gray-900/30 border-t border-gray-800/60">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Planos para cada perfil</h2>
          <p className="text-gray-400 mb-8">
            Do investidor iniciante ao escritório de arrematação. Comece grátis, faça upgrade quando precisar.
          </p>

          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { name: "Gratuito", price: "R$ 0", desc: "Para começar a explorar", highlight: false },
              { name: "Pro", price: "R$ 97/mês", desc: "Para investidores ativos", highlight: true },
              { name: "Premium", price: "R$ 197/mês", desc: "Para escritórios e fundos", highlight: false },
            ].map((p) => (
              <div
                key={p.name}
                className={`rounded-xl p-5 border ${
                  p.highlight
                    ? "border-blue-500/40 bg-blue-500/5"
                    : "border-gray-800 bg-gray-900"
                }`}
              >
                {p.highlight && (
                  <div className="text-xs text-blue-400 font-semibold mb-2">Mais popular</div>
                )}
                <div className="text-white font-bold text-sm mb-1">{p.name}</div>
                <div className={`text-lg font-black mb-1 ${p.highlight ? "text-blue-400" : "text-white"}`}>
                  {p.price}
                </div>
                <div className="text-gray-600 text-xs">{p.desc}</div>
              </div>
            ))}
          </div>

          <Link
            href="/planos"
            className="inline-block px-6 py-3 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white text-sm font-semibold rounded-xl transition-colors"
          >
            Ver todos os planos e funcionalidades →
          </Link>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="bg-gradient-to-br from-blue-600/10 to-blue-800/5 border border-blue-500/20 rounded-3xl p-12">
            <h2 className="text-4xl font-bold text-white mb-4">
              Encontre a oportunidade antes do concorrente
            </h2>
            <p className="text-gray-400 mb-8 text-lg">
              Cadastre-se agora e receba seu primeiro alerta ainda hoje.
            </p>
            <Link
              href="/login"
              className="inline-block px-10 py-4 bg-blue-600 hover:bg-blue-500 text-white font-bold text-base rounded-xl transition-colors shadow-xl shadow-blue-500/20"
            >
              Criar conta grátis →
            </Link>
            <p className="text-gray-600 text-sm mt-4">Sem compromisso · Cancele quando quiser</p>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-800/60 py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-blue-500 font-bold">⚖</span>
            <span className="font-semibold text-white">Mastavista</span>
            <span className="text-xs text-gray-600 ml-2">© 2026</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-600">
            <Link href="/planos" className="hover:text-gray-300 transition-colors">Planos</Link>
            <Link href="/login" className="hover:text-gray-300 transition-colors">Entrar</Link>
          </div>
          <p className="text-xs text-gray-700">
            Dados coletados de fontes públicas. Não constitui assessoria de investimento.
          </p>
        </div>
      </footer>
    </div>
  );
}
