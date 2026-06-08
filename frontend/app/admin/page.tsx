"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface CollectorStatus {
  total_active_properties: number;
  last_collection_at: string | null;
  new_today: number;
  alerts_sent_today: number;
}

interface HealthStatus {
  status: string;
  db: string;
}

const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];

export default function AdminPage() {
  const [uf, setUf] = useState("SP");
  const [collecting, setCollecting] = useState(false);
  const [collectMsg, setCollectMsg] = useState("");

  const { data: status, isLoading } = useQuery<CollectorStatus>({
    queryKey: ["admin", "status"],
    queryFn: () => api.get("/admin/status").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: health } = useQuery<HealthStatus>({
    queryKey: ["admin", "health"],
    queryFn: () => api.get("/admin/health").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const dbOk = health?.db === "connected";

  async function triggerCollect() {
    setCollecting(true);
    setCollectMsg("");
    try {
      await api.post("/admin/collect", { uf });
      setCollectMsg(`Coleta de ${uf} iniciada com sucesso.`);
    } catch {
      setCollectMsg("Erro ao iniciar coleta. Verifique os logs.");
    } finally {
      setCollecting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5">
        <h1 className="text-lg font-semibold text-white">Painel Admin</h1>
        <p className="text-xs text-gray-500 mt-0.5">Monitoramento e operações do sistema</p>
      </div>

      <div className="px-8 py-6 max-w-4xl space-y-5">
        {/* KPIs */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {[
            { label: "Imóveis ativos", value: isLoading ? "..." : String(status?.total_active_properties ?? 0) },
            { label: "Novos hoje", value: isLoading ? "..." : String(status?.new_today ?? 0) },
            { label: "Alertas hoje", value: isLoading ? "..." : String(status?.alerts_sent_today ?? 0) },
            { label: "Banco de dados", value: dbOk ? "Online" : health === undefined ? "..." : "Erro", ok: dbOk },
          ].map((item) => (
            <div key={item.label} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{item.label}</p>
              <p className={`text-2xl font-bold mt-2 ${"ok" in item ? (item.ok ? "text-emerald-400" : "text-red-400") : "text-white"}`}>
                {item.value}
              </p>
            </div>
          ))}
        </div>

        {/* Disparar coleta */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">Disparar coleta</h2>
            <p className="text-xs text-gray-500 mt-0.5">Executa o job de coleta da Caixa para um estado</p>
          </div>
          <div className="px-6 py-5 flex items-end gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Estado (UF)</label>
              <select
                value={uf}
                onChange={(e) => setUf(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <button
              onClick={triggerCollect}
              disabled={collecting || !dbOk}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
            >
              {collecting ? (
                <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Iniciando...</>
              ) : (
                <><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>Iniciar coleta {uf}</>
              )}
            </button>
            {collectMsg && (
              <p className={`text-xs ${collectMsg.includes("Erro") ? "text-red-400" : "text-emerald-400"}`}>
                {collectMsg}
              </p>
            )}
          </div>
        </div>

        {/* Coletores */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">Coletores</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left">
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Banco</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Última coleta</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              <tr>
                <td className="px-6 py-3.5 text-white font-medium">Caixa Econômica Federal</td>
                <td className="px-6 py-3.5 text-gray-400">
                  {status?.last_collection_at ? formatDate(status.last_collection_at) : "Nunca"}
                </td>
                <td className="px-6 py-3.5">
                  <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Ativo
                  </span>
                </td>
              </tr>
              {["Banco do Brasil", "BRB", "Banco do Nordeste", "Banco da Amazônia", "Banrisul", "Banestes"].map((banco) => (
                <tr key={banco}>
                  <td className="px-6 py-3.5 text-gray-500">{banco}</td>
                  <td className="px-6 py-3.5 text-gray-700">—</td>
                  <td className="px-6 py-3.5">
                    <span className="inline-flex items-center text-xs px-2.5 py-1 rounded-full font-medium bg-gray-800 text-gray-500 ring-1 ring-gray-700">
                      Fase 3
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
