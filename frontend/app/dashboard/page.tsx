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
  const { data: props, isLoading } = useProperties({}, 0, 8);
  const { data: status } = useQuery<AdminStatus>({
    queryKey: ["admin", "status"],
    queryFn: () => api.get("/admin/status").then((r) => r.data),
    refetchInterval: 60_000,
  });

  const kpis = [
    {
      label: "Imóveis ativos",
      value: status?.total_active_properties?.toLocaleString("pt-BR") ?? "—",
      icon: <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />,
    },
    {
      label: "Novos hoje",
      value: status?.new_today?.toLocaleString("pt-BR") ?? "—",
      icon: <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />,
    },
    {
      label: "Alertas enviados",
      value: status?.alerts_sent_today?.toLocaleString("pt-BR") ?? "—",
      icon: <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />,
    },
    {
      label: "Bancos",
      value: "1",
      sub: "Caixa · MVP Fase 1",
      icon: <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l9-3 9 3M3 6v12l9 3m-9-3l9 3m9-3V6m0 12l-9 3" />,
    },
  ];

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <div className="border-b border-gray-800 px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white">Dashboard</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {status?.last_collection_at
              ? `Última coleta em ${formatDate(status.last_collection_at)}`
              : "Aguardando primeira coleta"}
          </p>
        </div>
        <Link
          href="/imoveis"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Ver todos os imóveis
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>

      <div className="px-8 py-6 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {kpis.map((kpi) => (
            <div key={kpi.label} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{kpi.label}</p>
                <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  {kpi.icon}
                </svg>
              </div>
              <p className="text-2xl font-bold text-white tabular-nums">{kpi.value}</p>
              {"sub" in kpi && kpi.sub && <p className="text-xs text-gray-600 mt-1">{kpi.sub}</p>}
            </div>
          ))}
        </div>

        {/* Top oportunidades */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
            <div>
              <h2 className="text-sm font-semibold text-white">Top oportunidades</h2>
              <p className="text-xs text-gray-500 mt-0.5">Ordenado por score de oportunidade</p>
            </div>
            <Link href="/imoveis" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors">
              Ver todos
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (props?.items ?? []).length === 0 ? (
            <div className="py-16 text-center text-sm text-gray-500">
              Nenhum imóvel disponível. Aguardando coleta.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-left">
                    {["#", "Score", "Imóvel", "Tipo", "Preço", "Desconto", "Status"].map((h, i) => (
                      <th
                        key={h}
                        className={`px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                          i === 0 ? "pl-6 w-10" : i >= 4 && i <= 5 ? "text-right" : ""
                        } ${i === 6 ? "pr-6" : ""}`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {(props?.items ?? []).map((p, i) => (
                    <tr key={p.id} className="hover:bg-gray-800/40 transition-colors group">
                      <td className="pl-6 pr-4 py-3.5 text-xs text-gray-600 tabular-nums">{i + 1}</td>
                      <td className="px-4 py-3.5">
                        <ScoreBadge score={p.opportunity_score} />
                      </td>
                      <td className="px-4 py-3.5">
                        <Link href={`/imoveis/${p.id}`} className="font-medium text-white group-hover:text-blue-400 transition-colors">
                          {p.city}, {p.state}
                        </Link>
                        {p.neighborhood && <p className="text-xs text-gray-500 mt-0.5">{p.neighborhood}</p>}
                      </td>
                      <td className="px-4 py-3.5 text-gray-400">{p.property_type}</td>
                      <td className="px-4 py-3.5 font-semibold text-white text-right tabular-nums">
                        {formatCurrency(p.current_value)}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        {p.discount_percent ? (
                          <span className="font-semibold text-emerald-400">-{p.discount_percent}%</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="pl-4 pr-6 py-3.5">
                        <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium ring-1 ${
                          p.occupancy_status === "Desocupado"
                            ? "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 ring-amber-500/20"
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${p.occupancy_status === "Desocupado" ? "bg-emerald-400" : "bg-amber-400"}`} />
                          {p.occupancy_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Coletores */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl px-6 py-4">
          <h2 className="text-sm font-semibold text-white mb-4">Coletores</h2>
          <div className="flex items-center gap-3">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-sm text-gray-300 font-medium">Caixa Econômica Federal</span>
            <span className="text-gray-700">·</span>
            <span className="text-xs text-gray-500">Coleta 3× ao dia · 08h · 14h · 20h</span>
            <span className="ml-auto text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 font-medium">
              Online
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
