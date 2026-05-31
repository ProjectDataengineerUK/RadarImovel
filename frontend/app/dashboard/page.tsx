"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useProperties } from "@/hooks/useProperties";
import { formatCurrency, formatDate } from "@/lib/utils";
import ScoreBadge from "@/components/ScoreBadge";
import api from "@/lib/api";

interface AdminStatus {
  total_active_properties: number;
  last_collection_at: string | null;
  new_today: number;
  alerts_sent_today: number;
}

export default function DashboardPage() {
  const { data: props, isLoading } = useProperties({}, 0, 6);
  const { data: status } = useQuery<AdminStatus>({
    queryKey: ["admin", "status"],
    queryFn: () => api.get("/admin/status").then((r) => r.data),
    refetchInterval: 60_000,
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            {status?.last_collection_at
              ? `Última coleta: ${formatDate(status.last_collection_at)}`
              : "Aguardando primeira coleta"}
          </p>
        </div>
        <Link
          href="/imoveis"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Ver todos os imóveis →
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Imóveis monitorados"
          value={status ? String(status.total_active_properties) : "..."}
          sub="total ativo"
          accent="blue"
        />
        <KpiCard
          label="Novos hoje"
          value={status ? String(status.new_today) : "..."}
          sub="detectados nas últimas 24h"
          accent="green"
        />
        <KpiCard
          label="Alertas enviados"
          value={status ? String(status.alerts_sent_today) : "..."}
          sub="hoje via Telegram"
          accent="yellow"
        />
        <KpiCard
          label="Bancos ativos"
          value="1"
          sub="Caixa · MVP Fase 1"
          accent="purple"
        />
      </div>

      {/* Top Oportunidades */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">Top oportunidades</h2>
          <Link href="/imoveis" className="text-sm text-blue-400 hover:underline">Ver mais →</Link>
        </div>
        {isLoading ? (
          <p className="text-gray-500 py-6 text-center">Carregando...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  <th className="pb-3 pr-4">Score</th>
                  <th className="pb-3 pr-4">Localização</th>
                  <th className="pb-3 pr-4">Tipo</th>
                  <th className="pb-3 pr-4">Preço</th>
                  <th className="pb-3 pr-4">Desconto</th>
                  <th className="pb-3">Situação</th>
                </tr>
              </thead>
              <tbody>
                {(props?.items ?? []).map((p) => (
                  <tr key={p.id} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/40">
                    <td className="py-3 pr-4">
                      <ScoreBadge score={p.opportunity_score} />
                    </td>
                    <td className="py-3 pr-4">
                      <Link href={`/imoveis/${p.id}`} className="text-blue-400 hover:underline font-medium">
                        {p.city}/{p.state}
                      </Link>
                    </td>
                    <td className="py-3 pr-4 text-gray-400">{p.property_type}</td>
                    <td className="py-3 pr-4 font-semibold text-white">{formatCurrency(p.current_value)}</td>
                    <td className="py-3 pr-4">
                      {p.discount_percent
                        ? <span className="text-green-400 font-medium">{p.discount_percent}%</span>
                        : <span className="text-gray-500">—</span>}
                    </td>
                    <td className="py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        p.occupancy_status === "Desocupado"
                          ? "bg-green-900/50 text-green-400"
                          : "bg-orange-900/50 text-orange-400"
                      }`}>
                        {p.occupancy_status}
                      </span>
                    </td>
                  </tr>
                ))}
                {!isLoading && (props?.items ?? []).length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-gray-500">
                      Nenhum imóvel disponível. Aguardando coleta.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Status dos coletores */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Coletores</h2>
        <div className="flex items-center gap-3">
          <span className="inline-flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm text-gray-300">Caixa Econômica Federal</span>
          <span className="text-xs text-gray-500">· Coleta 3x/dia (08h · 14h · 20h)</span>
          <span className="ml-auto text-xs px-2 py-0.5 rounded bg-green-900/40 text-green-400">Ativo</span>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent: "blue" | "green" | "yellow" | "purple";
}) {
  const borderMap = {
    blue: "border-blue-800",
    green: "border-green-800",
    yellow: "border-yellow-800",
    purple: "border-purple-800",
  };
  const valueMap = {
    blue: "text-blue-400",
    green: "text-green-400",
    yellow: "text-yellow-400",
    purple: "text-purple-400",
  };
  return (
    <div className={`bg-gray-900 border ${borderMap[accent]} rounded-xl p-5`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-2 ${valueMap[accent]}`}>{value}</p>
      <p className="text-xs text-gray-600 mt-1">{sub}</p>
    </div>
  );
}
