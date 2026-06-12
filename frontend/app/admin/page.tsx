"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PLAN_DISPLAY } from "@/lib/entitlements";
import { formatDate } from "@/lib/utils";

interface Metrics {
  users_by_plan: { plan_code: string; plan_name: string; count: number }[];
  alerts_today: number;
  alerts_suppressed_today: number;
  connector_health: { bank_code: string; bank_name: string; last_seen_at: string | null }[];
}

interface CollectorStatus {
  total_active_properties: number;
  last_collection_at: string | null;
  new_today: number;
  alerts_sent_today: number;
}

const NAV = [
  { href: "/admin/planos", label: "Planos", description: "Features e limites por plano" },
  { href: "/admin/usuarios", label: "Usuários", description: "Buscar, atribuir plano e papel" },
  { href: "/admin/auditoria", label: "Auditoria", description: "Log de ações administrativas" },
];

export default function AdminPage() {
  const { data: metrics } = useQuery<Metrics>({
    queryKey: ["admin", "metrics"],
    queryFn: () => api.get("/admin/metrics").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: status } = useQuery<CollectorStatus>({
    queryKey: ["admin", "status"],
    queryFn: () => api.get("/admin/status").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const totalUsers = metrics?.users_by_plan.reduce((s, r) => s + r.count, 0) ?? 0;

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5">
        <h1 className="text-lg font-semibold text-white">Painel Admin</h1>
        <p className="text-xs text-gray-500 mt-0.5">Visão geral do sistema</p>
      </div>

      <div className="px-8 py-6 max-w-5xl space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {[
            { label: "Imóveis ativos", value: String(status?.total_active_properties ?? "—") },
            { label: "Novos hoje", value: String(status?.new_today ?? "—") },
            { label: "Alertas hoje", value: String(metrics?.alerts_today ?? "—") },
            { label: "Usuários", value: String(totalUsers || "—") },
          ].map((item) => (
            <div key={item.label} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{item.label}</p>
              <p className="text-2xl font-bold mt-2 text-white">{item.value}</p>
            </div>
          ))}
        </div>

        {/* Usuários por plano */}
        {metrics?.users_by_plan && metrics.users_by_plan.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-white mb-4">Usuários por plano</h2>
            <div className="flex gap-6">
              {metrics.users_by_plan.map((r) => (
                <div key={r.plan_code} className="text-center">
                  <p className={`text-2xl font-bold ${PLAN_DISPLAY[r.plan_code]?.color ?? "text-white"}`}>
                    {r.count}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{r.plan_name}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Navegação do painel */}
        <div className="grid grid-cols-3 gap-4">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="bg-gray-900 border border-gray-800 hover:border-gray-600 rounded-xl p-5 transition-colors group"
            >
              <h3 className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors">
                {item.label}
              </h3>
              <p className="text-xs text-gray-500 mt-1">{item.description}</p>
            </Link>
          ))}
        </div>

        {/* Coletores */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">Saúde dos coletores</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left">
                {["Banco", "Última coleta", "Status"].map((h) => (
                  <th key={h} className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {(metrics?.connector_health ?? []).map((c) => {
                const ok = !!c.last_seen_at;
                return (
                  <tr key={c.bank_code}>
                    <td className="px-6 py-3.5 text-white font-medium">{c.bank_name}</td>
                    <td className="px-6 py-3.5 text-gray-400">
                      {c.last_seen_at ? formatDate(c.last_seen_at) : "Nunca"}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium ${
                        ok
                          ? "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20"
                          : "bg-gray-800 text-gray-500 ring-1 ring-gray-700"
                      }`}>
                        {ok && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
                        {ok ? "Ativo" : "Pendente"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
