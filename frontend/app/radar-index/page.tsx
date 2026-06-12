"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";

interface RadarEntry {
  period: string;
  state: string;
  bank_code: string | null;
  property_type: string | null;
  sample_size: number;
  avg_discount_pct: number;
  median_discount_pct: number;
  p25_discount_pct: number | null;
  p75_discount_pct: number | null;
}

interface RadarIndexResponse {
  period: string;
  entries: RadarEntry[];
}

async function fetchIndex(period?: string, state?: string): Promise<RadarIndexResponse> {
  const params: Record<string, string> = {};
  if (period) params.period = period;
  if (state) params.state = state;
  const { data } = await api.get("/radar-index", { params });
  return data;
}

const STATES = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
  "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO",
];

function DiscountBadge({ value }: { value: number }) {
  const color =
    value >= 40 ? "bg-green-100 text-green-800" :
    value >= 25 ? "bg-yellow-100 text-yellow-800" :
    "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {value.toFixed(1)}%
    </span>
  );
}

export default function RadarIndexPage() {
  const [filterState, setFilterState] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["radar-index", filterState],
    queryFn: () => fetchIndex(undefined, filterState || undefined),
  });

  const stateAgg = data?.entries.filter(
    (e) => e.bank_code === null && e.property_type === null
  ) ?? [];

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Radar Index — Índice de Deságio em Leilões
        </h1>
        <p className="mt-2 text-gray-500 text-sm">
          Deságio médio de imóveis de bancos públicos por estado no Brasil.
          Período: <span className="font-medium">{data?.period ?? "—"}</span>
        </p>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <label className="text-sm text-gray-600 font-medium">Filtrar por UF:</label>
        <select
          value={filterState}
          onChange={(e) => setFilterState(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos</option>
          {STATES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="space-y-3 animate-pulse">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && stateAgg.length === 0 && (
        <p className="text-gray-500 text-sm">Nenhum dado disponível para o período selecionado.</p>
      )}

      {!isLoading && stateAgg.length > 0 && (
        <div className="overflow-hidden border rounded-xl">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Estado</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Deságio médio</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Mediana</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">P25 / P75</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Imóveis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {stateAgg
                .sort((a, b) => b.avg_discount_pct - a.avg_discount_pct)
                .map((row) => (
                  <tr key={row.state} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{row.state}</td>
                    <td className="px-4 py-3 text-right">
                      <DiscountBadge value={row.avg_discount_pct} />
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {row.median_discount_pct.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500 text-xs">
                      {row.p25_discount_pct?.toFixed(1) ?? "—"} /{" "}
                      {row.p75_discount_pct?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500">
                      {row.sample_size.toLocaleString("pt-BR")}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-6 text-xs text-gray-400 text-center">
        Dados calculados mensalmente com base nos imóveis ativos monitorados pelo Radar Imóvel.
      </p>
    </main>
  );
}
