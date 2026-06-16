"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";

// ── Types ────────────────────────────────────────────────────────────────────

interface ConnectorHealth {
  bank_code: string;
  bank_name: string;
  source_type: string;
  tos_compliant: boolean;
  last_seen_at: string | null;
  property_count: number;
}

interface Metrics {
  alerts_today: number;
  alerts_suppressed_today: number;
  alerts_sent_today: number;
  alerts_failed_today: number;
  connector_health: ConnectorHealth[];
}

interface LLMOpsData {
  total_documents: number;
  pending: number;
  processed_today: number;
  failed_today: number;
  total_processed: number;
  total_failed: number;
  success_rate_pct: number;
  avg_confidence: number | null;
  confidence_distribution: { high: number; medium: number; low: number };
  recent_errors: { id: string; property_id: string | null; processing_error: string | null; processed_at: string | null }[];
}

interface MLOpsData {
  score: {
    total_properties: number;
    scored: number;
    coverage_pct: number;
    avg_score: number | null;
    distribution: Record<string, number>;
  };
  risk: {
    total: number;
    coverage_pct: number;
    avg_total_score: number | null;
    by_level: Record<string, number>;
    latest_version: string;
  };
  prediction: {
    total: number;
    coverage_pct: number;
    model_versions: { version: string; count: number }[];
    avg_expected_drop_30d_pct: number | null;
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const SOURCE_TYPE_LABEL: Record<string, string> = {
  bank: "Banco", auctioneer: "Leiloeiro", judicial: "Judicial",
};
const SOURCE_TYPE_COLOR: Record<string, string> = {
  bank: "text-blue-400 bg-blue-500/10",
  auctioneer: "text-emerald-400 bg-emerald-500/10",
  judicial: "text-amber-400 bg-amber-500/10",
};
const RISK_LEVEL_COLOR: Record<string, string> = {
  baixo: "text-emerald-400", medio: "text-amber-400",
  alto: "text-orange-400", critico: "text-red-500",
};

function staleness(lastSeen: string | null): "ok" | "warn" | "stale" | "never" {
  if (!lastSeen) return "never";
  const h = (Date.now() - new Date(lastSeen).getTime()) / 3_600_000;
  if (h < 24) return "ok";
  if (h < 72) return "warn";
  return "stale";
}

const STATUS_CFG = {
  ok:    { label: "OK",     dot: "bg-emerald-400", badge: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20" },
  warn:  { label: "Lento",  dot: "bg-amber-400",   badge: "bg-amber-500/10 text-amber-400 ring-amber-500/20" },
  stale: { label: "Parado", dot: "bg-red-500",      badge: "bg-red-500/10 text-red-400 ring-red-500/20" },
  never: { label: "Nunca",  dot: "bg-gray-600",     badge: "bg-gray-800 text-gray-500 ring-gray-700" },
} as const;

function Kpi({ label, value, sub, warn }: { label: string; value: React.ReactNode; sub?: string; warn?: boolean }) {
  return (
    <div className={`bg-gray-900 border rounded-xl p-5 ${warn ? "border-red-800/40" : "border-gray-800"}`}>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-2xl font-bold ${warn ? "text-red-400" : "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-2">{sub}</p>}
    </div>
  );
}

function CovBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400">{pct}%</span>
    </div>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

function DataOpsTab({ metrics, refetch }: { metrics?: Metrics; refetch: () => void }) {
  const sources = metrics?.connector_health ?? [];
  const groups: Record<string, ConnectorHealth[]> = { bank: [], auctioneer: [], judicial: [] };
  for (const c of sources) { (groups[c.source_type] ??= []).push(c); }

  const staleN = sources.filter((c) => { const s = staleness(c.last_seen_at); return s === "stale" || s === "never"; }).length;
  const warnN  = sources.filter((c) => staleness(c.last_seen_at) === "warn").length;
  const okN    = sources.filter((c) => staleness(c.last_seen_at) === "ok").length;

  const delivTotal = (metrics?.alerts_sent_today ?? 0) + (metrics?.alerts_failed_today ?? 0);
  const delivRate  = delivTotal > 0 ? Math.round((metrics!.alerts_sent_today / delivTotal) * 100) : 100;

  return (
    <div className="space-y-8">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Kpi label="Fontes ativas" value={sources.length} sub={`${okN} OK · ${warnN} lento · ${staleN} parado`} />
        <Kpi label="Anomalias" value={staleN + warnN} warn={staleN > 0} sub={`${staleN} parado · ${warnN} lento`} />
        <Kpi label="Alertas hoje" value={metrics?.alerts_today ?? "—"} sub={`${metrics?.alerts_suppressed_today ?? 0} suprimidos`} />
        <Kpi label="Taxa de entrega" value={`${delivRate}%`} warn={delivRate < 90}
          sub={`${metrics?.alerts_sent_today ?? 0} enviados · ${metrics?.alerts_failed_today ?? 0} falhas`} />
      </div>

      {/* Source cards */}
      {([ ["bank","Bancos públicos"], ["auctioneer","Leiloeiros e portais"], ["judicial","Hastas judiciais"] ] as [string,string][]).map(([type, label]) => {
        const items = groups[type] ?? [];
        if (!items.length) return null;
        return (
          <section key={type}>
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">{label}</h3>
              <div className="flex-1 h-px bg-gray-800" />
              <span className="text-xs text-gray-600">{items.length} fonte{items.length !== 1 ? "s" : ""}</span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {items.map((c) => {
                const st = staleness(c.last_seen_at);
                const cfg = STATUS_CFG[st];
                return (
                  <div key={c.bank_code} className={`bg-gray-900 border rounded-xl p-4 ${
                    st === "stale" || st === "never" ? "border-red-800/40" :
                    st === "warn" ? "border-amber-800/30" : "border-gray-800"
                  }`}>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div>
                        <p className="text-white font-medium text-sm">{c.bank_name}</p>
                        <span className={`inline-block mt-1 text-[10px] font-semibold px-1.5 py-0.5 rounded ${SOURCE_TYPE_COLOR[c.source_type] ?? "text-gray-400 bg-gray-800"}`}>
                          {SOURCE_TYPE_LABEL[c.source_type] ?? c.source_type}
                        </span>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full font-medium ring-1 shrink-0 ${cfg.badge}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${st === "ok" ? "animate-pulse" : ""}`} />
                        {cfg.label}
                      </span>
                    </div>
                    <div className="space-y-1 text-xs text-gray-500">
                      <div className="flex justify-between">
                        <span>Última coleta</span>
                        <span className={`font-medium ${st === "ok" ? "text-gray-300" : st === "warn" ? "text-amber-400" : "text-red-400"}`}>
                          {c.last_seen_at ? formatDate(c.last_seen_at) : "Nunca"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Imóveis</span>
                        <span className="font-mono text-gray-300">{c.property_count.toLocaleString("pt-BR")}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-600 pt-2 border-t border-gray-800">
        <span className="text-gray-500 font-medium">Semáforo:</span>
        {Object.entries(STATUS_CFG).map(([k, v]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${v.dot}`} />
            {v.label} {k === "ok" ? "(<24h)" : k === "warn" ? "(24–72h)" : k === "stale" ? "(>72h)" : ""}
          </span>
        ))}
        <span className="ml-auto">Atualiza a cada 30 s</span>
      </div>
    </div>
  );
}

function LLMOpsTab({ data }: { data?: LLMOpsData }) {
  if (!data) return <div className="flex justify-center py-12"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;

  const confPct = data.avg_confidence != null ? Math.round(data.avg_confidence * 100) : null;
  const confTotal = data.confidence_distribution.high + data.confidence_distribution.medium + data.confidence_distribution.low;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Kpi label="Total editais" value={data.total_documents.toLocaleString("pt-BR")} sub={`${data.pending} pendentes`} />
        <Kpi label="Processados hoje" value={data.processed_today} sub={`${data.failed_today} falhas hoje`} warn={data.failed_today > 0} />
        <Kpi label="Taxa de sucesso" value={`${data.success_rate_pct}%`} warn={data.success_rate_pct < 90}
          sub={`${data.total_processed} ok · ${data.total_failed} erro`} />
        <Kpi label="Confiança média"
          value={confPct != null ? `${confPct}%` : "—"}
          warn={confPct != null && confPct < 70}
          sub="threshold: 75%" />
      </div>

      {/* Distribuição de confiança */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-5">Distribuição de confiança (Gemini)</h3>
        <div className="space-y-4">
          {([
            ["Alta (≥ 80%)", data.confidence_distribution.high, "bg-emerald-500"],
            ["Média (60–79%)", data.confidence_distribution.medium, "bg-amber-500"],
            ["Baixa (< 60%)", data.confidence_distribution.low, "bg-red-500"],
          ] as [string, number, string][]).map(([label, n, color]) => {
            const pct = confTotal > 0 ? (n / confTotal) * 100 : 0;
            return (
              <div key={label}>
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>{label}</span>
                  <span className="font-mono">{n} ({pct.toFixed(1)}%)</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Erros recentes */}
      {data.recent_errors.length > 0 && (
        <div className="bg-gray-900 border border-red-900/30 rounded-xl">
          <div className="px-6 py-4 border-b border-gray-800">
            <h3 className="text-sm font-semibold text-white">Erros recentes de extração</h3>
          </div>
          <div className="divide-y divide-gray-800">
            {data.recent_errors.map((e) => (
              <div key={e.id} className="px-6 py-3 flex items-start gap-4">
                <span className="text-red-400 text-xs mt-0.5 shrink-0">✗</span>
                <div className="min-w-0">
                  <p className="text-xs text-gray-300 truncate">{e.processing_error ?? "Erro desconhecido"}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">
                    {e.processed_at ? formatDate(e.processed_at) : "—"}
                    {e.property_id && <span className="ml-2 font-mono">{e.property_id.slice(0, 8)}…</span>}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MLOpsTab({ data }: { data?: MLOpsData }) {
  if (!data) return <div className="flex justify-center py-12"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;

  const SCORE_BANDS = ["0-19", "20-39", "40-59", "60-79", "80-100"];
  const BAND_COLOR = ["bg-red-500", "bg-orange-500", "bg-amber-500", "bg-emerald-500", "bg-blue-500"];
  const maxBandCount = Math.max(1, ...SCORE_BANDS.map((b) => data.score.distribution[b] ?? 0));

  return (
    <div className="space-y-8">
      {/* Coverage KPIs */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Score de oportunidade</p>
          <p className="text-2xl font-bold text-white">{data.score.avg_score ?? "—"}</p>
          <p className="text-xs text-gray-600 mt-1">média · {data.score.scored.toLocaleString("pt-BR")} imóveis</p>
          <CovBar pct={data.score.coverage_pct} />
          <p className="text-[10px] text-gray-700 mt-1">cobertura: {data.score.coverage_pct}%</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Risco multidimensional</p>
          <p className="text-2xl font-bold text-white">{data.risk.avg_total_score ?? "—"}</p>
          <p className="text-xs text-gray-600 mt-1">score médio · v{data.risk.latest_version}</p>
          <CovBar pct={data.risk.coverage_pct} />
          <p className="text-[10px] text-gray-700 mt-1">cobertura: {data.risk.coverage_pct}%</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Predição de preço</p>
          <p className="text-2xl font-bold text-white">
            {data.prediction.avg_expected_drop_30d_pct != null ? `${data.prediction.avg_expected_drop_30d_pct}%` : "—"}
          </p>
          <p className="text-xs text-gray-600 mt-1">queda média esperada / 30 dias</p>
          <CovBar pct={data.prediction.coverage_pct} />
          <p className="text-[10px] text-gray-700 mt-1">cobertura: {data.prediction.coverage_pct}%</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Histograma de score */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-5">Distribuição de score de oportunidade</h3>
          <div className="space-y-3">
            {SCORE_BANDS.map((band, i) => {
              const n = data.score.distribution[band] ?? 0;
              const pct = maxBandCount > 0 ? (n / maxBandCount) * 100 : 0;
              return (
                <div key={band}>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{band}</span>
                    <span className="font-mono">{n.toLocaleString("pt-BR")}</span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`h-full ${BAND_COLOR[i]} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Risco por nível */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-5">Risco: distribuição por nível</h3>
          {Object.keys(data.risk.by_level).length === 0 ? (
            <p className="text-sm text-gray-600">Nenhum score de risco calculado ainda.</p>
          ) : (
            <div className="space-y-3">
              {(["baixo", "medio", "alto", "critico"] as const).map((level) => {
                const n = data.risk.by_level[level] ?? 0;
                const total = data.risk.total || 1;
                const pct = Math.round((n / total) * 100);
                return (
                  <div key={level}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className={`capitalize ${RISK_LEVEL_COLOR[level] ?? "text-gray-400"}`}>{level}</span>
                      <span className="font-mono text-gray-400">{n.toLocaleString("pt-BR")} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${RISK_LEVEL_COLOR[level]?.replace("text-", "bg-").replace("-400", "-500").replace("-500", "-500") ?? "bg-gray-500"}`}
                        style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Versões de modelo */}
          {data.prediction.model_versions.length > 0 && (
            <div className="mt-6 border-t border-gray-800 pt-4">
              <p className="text-xs text-gray-500 mb-2">Versões do modelo de predição</p>
              <div className="flex flex-wrap gap-2">
                {data.prediction.model_versions.map((mv) => (
                  <span key={mv.version} className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 font-mono text-gray-300">
                    v{mv.version} <span className="text-gray-500">({mv.count})</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

type Tab = "dataops" | "llmops" | "mlops";

const TABS: { id: Tab; label: string; badge: string }[] = [
  { id: "dataops", label: "DataOps", badge: "Coletores & Alertas" },
  { id: "llmops", label: "LLMOps",  badge: "Gemini / Editais" },
  { id: "mlops",  label: "MLOps",   badge: "Score & Risco & Predição" },
];

export default function SentinelaPage() {
  const [tab, setTab] = useState<Tab>("dataops");

  const metricsQ = useQuery<Metrics>({
    queryKey: ["admin", "sentinel-metrics"],
    queryFn: () => api.get("/admin/metrics").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const llmopsQ = useQuery<LLMOpsData>({
    queryKey: ["admin", "sentinel-llmops"],
    queryFn: () => api.get("/admin/sentinel/llmops").then((r) => r.data),
    enabled: tab === "llmops",
    refetchInterval: 60_000,
  });

  const mlopsQ = useQuery<MLOpsData>({
    queryKey: ["admin", "sentinel-mlops"],
    queryFn: () => api.get("/admin/sentinel/mlops").then((r) => r.data),
    enabled: tab === "mlops",
    refetchInterval: 60_000,
  });

  const sources = metricsQ.data?.connector_health ?? [];
  const staleN = sources.filter((c) => { const s = staleness(c.last_seen_at); return s === "stale" || s === "never"; }).length;
  const anomalyCount = staleN + (sources.filter((c) => staleness(c.last_seen_at) === "warn").length);

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 px-8 py-5 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h1 className="text-lg font-semibold text-white">Sentinela</h1>
            {anomalyCount > 0 && (
              <span className="text-xs bg-red-500/10 text-red-400 border border-red-500/20 rounded-full px-2 py-0.5 font-medium">
                {anomalyCount} anomalia{anomalyCount !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500">Observabilidade: DataOps · LLMOps · MLOps</p>
        </div>
        <button
          onClick={() => { metricsQ.refetch(); llmopsQ.refetch(); mlopsQ.refetch(); }}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg px-3 py-1.5 transition-colors"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Atualizar
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-8">
        <div className="flex gap-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`relative px-5 py-3.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === t.id
                  ? "text-white border-blue-500"
                  : "text-gray-500 border-transparent hover:text-gray-300 hover:border-gray-600"
              }`}
            >
              <span>{t.label}</span>
              <span className="ml-2 text-[10px] text-gray-600 hidden md:inline">{t.badge}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-8 py-6 max-w-6xl">
        {tab === "dataops" && <DataOpsTab metrics={metricsQ.data} refetch={metricsQ.refetch} />}
        {tab === "llmops" && <LLMOpsTab data={llmopsQ.data} />}
        {tab === "mlops"  && <MLOpsTab  data={mlopsQ.data} />}
      </div>
    </div>
  );
}
