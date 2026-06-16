"use client";

import { useState } from "react";
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

const FAQ = [
  {
    q: "Os dados são em tempo real?",
    a: "Monitoramos todas as fontes de hora em hora. Quando um imóvel novo aparece ou o preço muda, você recebe o alerta em menos de 1 minuto via Telegram.",
  },
  {
    q: "O que é 2ª Praça?",
    a: "Quando um imóvel não é arrematado na 1ª Praça, ele vai a leilão novamente — a 2ª Praça — com lance mínimo reduzido em ≥ 40%. Detectamos isso automaticamente e alertamos antes de todo mundo.",
  },
  {
    q: "Preciso de cartão de crédito para o plano gratuito?",
    a: "Não. Faça login com Google e já começa a usar. Nenhum dado de pagamento é exigido no plano gratuito.",
  },
  {
    q: "Funciona para qualquer estado do Brasil?",
    a: "Sim. Monitoramos imóveis em todos os 27 estados e no Distrito Federal, em todas as fontes ativas.",
  },
  {
    q: "Os dados dos editais são confiáveis?",
    a: "Coletamos diretamente dos sites oficiais dos bancos e do DataJud/CNJ. O Gemini lê o PDF original do edital — sem intermediários.",
  },
  {
    q: "Posso cancelar a qualquer momento?",
    a: "Sim. Sem multa e sem fidelidade. O plano volta para o gratuito imediatamente ao cancelar.",
  },
];

function PropertyMock() {
  return (
    <div className="relative w-full max-w-sm mx-auto lg:mx-0">
      {/* Glow */}
      <div className="absolute inset-0 bg-blue-500/10 blur-3xl rounded-3xl" />

      <div className="relative bg-gray-900 border border-gray-700/60 rounded-2xl overflow-hidden shadow-2xl">
        {/* Image placeholder */}
        <div className="h-36 bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center relative">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(37,99,235,0.15),transparent)]" />
          <span className="text-5xl relative z-10">🏢</span>
          {/* 2ª Praça badge */}
          <div className="absolute top-3 left-3 bg-amber-500 text-black text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-wide">
            2ª Praça
          </div>
          {/* Novo badge */}
          <div className="absolute top-3 right-3 flex items-center gap-1 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-[10px] font-semibold px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            Novo
          </div>
        </div>

        <div className="p-4 space-y-3">
          {/* Title */}
          <div>
            <p className="text-white font-semibold text-sm">Apartamento 72m² — Moema</p>
            <p className="text-gray-500 text-xs mt-0.5">São Paulo, SP · Caixa Econômica Federal</p>
          </div>

          {/* Price */}
          <div className="flex items-end gap-3">
            <div>
              <p className="text-xs text-gray-600 line-through">Avaliado: R$ 680.000</p>
              <p className="text-2xl font-black text-white">R$ 389.000</p>
            </div>
            <span className="mb-1 bg-emerald-500/15 text-emerald-400 text-xs font-bold px-2 py-0.5 rounded-lg">
              −43%
            </span>
          </div>

          {/* Score */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500">Score de oportunidade</span>
              <span className="text-xs font-bold text-blue-400">87 / 100</span>
            </div>
            <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full" style={{ width: "87%" }} />
            </div>
          </div>

          {/* Tags */}
          <div className="flex gap-1.5 flex-wrap">
            {["Desocupado", "ITBI quitado", "Edital lido ✓"].map((t) => (
              <span key={t} className="text-[10px] text-gray-400 bg-gray-800 border border-gray-700 px-2 py-0.5 rounded-md">
                {t}
              </span>
            ))}
          </div>

          <button className="w-full bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold py-2 rounded-xl transition-colors">
            Ver detalhes + ROI →
          </button>
        </div>
      </div>

      {/* Notification pop */}
      <div className="absolute -bottom-4 -right-4 bg-gray-900 border border-gray-700 rounded-xl px-3 py-2 shadow-xl flex items-center gap-2">
        <span className="text-lg">🔔</span>
        <div>
          <p className="text-white text-[11px] font-semibold">Novo alerta!</p>
          <p className="text-gray-500 text-[10px]">Caixa · SP · há 23 seg</p>
        </div>
      </div>
    </div>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-800 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-4 text-left gap-4 group"
      >
        <span className="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">
          {q}
        </span>
        <span className={`text-gray-600 text-lg shrink-0 transition-transform ${open ? "rotate-45" : ""}`}>
          +
        </span>
      </button>
      {open && (
        <p className="text-sm text-gray-500 leading-relaxed pb-4">{a}</p>
      )}
    </div>
  );
}

export default function LandingPage() {
  const { user, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-gray-800/60 bg-gray-950/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <span className="text-blue-500 text-xl font-bold">⚖</span>
            <span className="text-white font-bold text-lg tracking-tight">Mastavista</span>
          </div>

          {/* Links desktop */}
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-400">
            <a href="#funcionalidades" className="hover:text-white transition-colors">Funcionalidades</a>
            <a href="#fontes" className="hover:text-white transition-colors">Fontes</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
            <Link href="/planos" className="hover:text-white transition-colors">Planos</Link>
          </div>

          {/* Botões desktop */}
          <div className="hidden md:flex items-center gap-2">
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
                  <Link
                    href="/login"
                    className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    Entrar
                  </Link>
                  <Link
                    href="/cadastro"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition-colors"
                  >
                    Cadastrar grátis
                  </Link>
                </>
              )
            )}
          </div>

          {/* Hamburger mobile */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 text-gray-400 hover:text-white transition-colors"
            aria-label="Menu"
          >
            {menuOpen ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Menu mobile */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-950 px-6 py-4 space-y-1">
            <a href="#funcionalidades" onClick={() => setMenuOpen(false)} className="block py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Funcionalidades</a>
            <a href="#fontes" onClick={() => setMenuOpen(false)} className="block py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Fontes</a>
            <a href="#faq" onClick={() => setMenuOpen(false)} className="block py-2.5 text-sm text-gray-400 hover:text-white transition-colors">FAQ</a>
            <Link href="/planos" onClick={() => setMenuOpen(false)} className="block py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Planos</Link>
            <div className="pt-3 flex flex-col gap-2">
              {!loading && (
                user ? (
                  <Link href="/dashboard" className="w-full text-center px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg">
                    Ir para o painel →
                  </Link>
                ) : (
                  <>
                    <Link href="/cadastro" className="w-full text-center px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg">
                      Cadastrar grátis
                    </Link>
                    <Link href="/login" className="w-full text-center px-4 py-2.5 border border-gray-700 text-gray-300 text-sm font-medium rounded-lg">
                      Entrar
                    </Link>
                  </>
                )
              )}
            </div>
          </div>
        )}
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-20 pb-20 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(37,99,235,0.15),transparent)]" />
        <div className="relative max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-14 items-center">
            {/* Left */}
            <div>
              <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-sm text-blue-400 mb-7">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                16 fontes monitoradas em tempo real
              </div>

              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight leading-tight mb-5">
                Inteligência em{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-600">
                  leilões imobiliários
                </span>
              </h1>

              <p className="text-lg text-gray-400 mb-8 leading-relaxed">
                Monitore Caixa, BB, BRB e mais 13 fontes. Receba alertas antes do mercado,
                leia editais com IA e calcule o ROI em segundos.
              </p>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
                <Link
                  href="/cadastro"
                  className="px-7 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-colors text-base shadow-lg shadow-blue-500/20"
                >
                  Começar grátis →
                </Link>
                <Link
                  href="/planos"
                  className="px-7 py-3.5 bg-gray-800 hover:bg-gray-700 text-white font-semibold rounded-xl transition-colors text-base border border-gray-700"
                >
                  Ver planos
                </Link>
              </div>

              <p className="text-sm text-gray-600">Sem cartão de crédito · Login com Google em segundos</p>
            </div>

            {/* Right — mock card */}
            <div className="flex justify-center lg:justify-end">
              <PropertyMock />
            </div>
          </div>
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
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-white mb-4">Tudo que você precisa para decidir rápido</h2>
            <p className="text-gray-400 max-w-xl mx-auto">Do alerta à análise de risco — sem precisar abrir 10 abas.</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-gray-900 border border-gray-800 rounded-2xl p-5 hover:border-gray-700 transition-colors"
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
            <p className="text-gray-400">A maior cobertura de leilões imobiliários bancários e judiciais do Brasil.</p>
          </div>

          <div className="space-y-8">
            {[
              { label: "Bancos públicos", color: "text-blue-400 bg-blue-500/10", items: BANKS },
              { label: "Leiloeiros e portais", color: "text-emerald-400 bg-emerald-500/10", items: AUCTIONEERS },
              { label: "Hastas judiciais", color: "text-amber-400 bg-amber-500/10", items: JUDICIAL },
            ].map(({ label, color, items }) => (
              <div key={label}>
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-600 mb-4">{label}</p>
                <div className="flex flex-wrap gap-2">
                  {items.map((item) => (
                    <span
                      key={item.name}
                      className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
                    >
                      <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${color}`}>
                        {item.tag}
                      </span>
                      {item.name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
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
                  p.highlight ? "border-blue-500/40 bg-blue-500/5" : "border-gray-800 bg-gray-900"
                }`}
              >
                {p.highlight && <div className="text-xs text-blue-400 font-semibold mb-2">Mais popular</div>}
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

      {/* ── FAQ ─────────────────────────────────────────────────────── */}
      <section id="faq" className="py-24 px-6">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Perguntas frequentes</h2>
            <p className="text-gray-400">Tudo que você precisa saber antes de começar.</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-2xl px-6">
            {FAQ.map((item) => (
              <FaqItem key={item.q} q={item.q} a={item.a} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────── */}
      <section className="py-24 px-6 bg-gray-900/30 border-t border-gray-800/60">
        <div className="max-w-3xl mx-auto text-center">
          <div className="bg-gradient-to-br from-blue-600/10 to-blue-800/5 border border-blue-500/20 rounded-3xl p-12">
            <h2 className="text-4xl font-bold text-white mb-4">
              Encontre a oportunidade antes do concorrente
            </h2>
            <p className="text-gray-400 mb-8 text-lg">
              Cadastre-se agora e receba seu primeiro alerta ainda hoje.
            </p>
            <Link
              href="/cadastro"
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
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-6">
            <div className="flex items-center gap-2">
              <span className="text-blue-500 font-bold">⚖</span>
              <span className="font-semibold text-white">Mastavista</span>
              <span className="text-xs text-gray-600 ml-2">© 2026</span>
            </div>

            <div className="flex items-center gap-6 text-sm text-gray-600">
              <Link href="/planos" className="hover:text-gray-300 transition-colors">Planos</Link>
              <Link href="/login" className="hover:text-gray-300 transition-colors">Entrar</Link>
              <Link href="/cadastro" className="hover:text-gray-300 transition-colors">Cadastrar</Link>
              <Link href="/privacidade" className="hover:text-gray-300 transition-colors">Privacidade</Link>
              <Link href="/termos" className="hover:text-gray-300 transition-colors">Termos</Link>
            </div>
          </div>

          <p className="text-center text-xs text-gray-700">
            Dados coletados de fontes públicas. Não constitui assessoria de investimento.
            Mastavista não é corretora nem leiloeiro credenciado.
          </p>
        </div>
      </footer>
    </div>
  );
}
