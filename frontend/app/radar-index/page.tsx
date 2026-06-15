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

interface CityEntry {
  city: string;
  uf: string;
  sample_size: number;
  avg_discount_pct: number;
  median_discount_pct: number;
  trend_delta: number | null;
}

interface RadarIndexResponse {
  period: string;
  entries: RadarEntry[];
}

interface CityIndexResponse {
  entries: CityEntry[];
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

function TrendArrow({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-gray-400">—</span>;
  if (delta > 0.5) return <span className="text-green-600 font-medium">+{delta.toFixed(1)}% ↑</span>;
  if (delta < -0.5) return <span className="text-red-500 font-medium">{delta.toFixed(1)}% ↓</span>;
  return <span className="text-gray-500">~</span>;
}

export default function RadarIndexPage() {
  const [filterState, setFilterState] = useState("");
  const [granularity, setGranularity] = useState<"state" | "city">("state");

  const stateQuery = useQuery({
    queryKey: ["radar-index", "state", filterState],
    queryFn: async (): Promise<RadarIndexResponse> => {
      const params: Record<string, string> = { granularity: "state" };
      if (filterState) params.state = filterState;
      const { data } = await api.get("/radar-index", { params });
      return data;
    },
    enabled: granularity === "state",
  });

  const cityQuery = useQuery({
    queryKey: ["radar-index", "city", filterState],
    queryFn: async (): Promise<CityIndexResponse> => {
      const params: Record<string, string> = { granularity: "city" };
      if (filterState) params.state = filterState;
      const { data } = await api.get("/radar-index", { params });
      return data;
    },
    enabled: granularity === "city",
  });

  const isLoading = granularity === "state" ? stateQuery.isLoading : cityQuery.isLoading;
  const stateAgg = stateQuery.data?.entries.filter(
    (e) => e.bank_code === null && e.property_type === null
  ) ?? [];
  const cityEntries = cityQuery.data?.entries ?? [];

  return (
    <main className="p-6 max-w-5xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            Radar Index — Índice de Deságio em Leilões
          </h1>
          <p className="mt-2 text-gray-500 text-sm">
            Deságio médio de imóveis de bancos públicos no Brasil.
            {granularity === "state" && stateQuery.data?.period && (
              <> Período: <span className="font-medium">{stateQuery.data.period}</span></>
            )}
          </p>
        </div>

        {/* Controls */}
        <div className="mb-6 flex flex-wrap items-center gap-4">
          <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
            <button
              onClick={() => setGranularity("state")}
              className={`px-4 py-2 transition-colors ${granularity === "state" ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              Por Estado
            </button>
            <button
              onClick={() => setGranularity("city")}
              className={`px-4 py-2 transition-colors ${granularity === "city" ? "bg-blue-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              Por Município
            </button>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 font-medium">UF:</label>
            <select
              value={filterState}
              onChange={(e) => setFilterState(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              {STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>

        {isLoading && (
          <div className="space-y-3 animate-pulse">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded-lg" />
            ))}
          </div>
        )}

        {/* State view */}
        {!isLoading && granularity === "state" && (
          stateAgg.length === 0 ? (
            <p className="text-gray-500 text-sm">Nenhum dado disponível para o período selecionado.</p>
          ) : (
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
          )
        )}

        {/* City view */}
        {!isLoading && granularity === "city" && (
          cityEntries.length === 0 ? (
            <p className="text-gray-500 text-sm">Nenhum dado disponível.</p>
          ) : (
            <div className="overflow-hidden border rounded-xl">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">Município</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">UF</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-500">Deságio médio</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-500">Mediana</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-500">Tendência</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-500">Imóveis</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {cityEntries.map((row) => (
                    <tr key={`${row.city}-${row.uf}`} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{row.city}</td>
                      <td className="px-4 py-3 text-gray-500">{row.uf}</td>
                      <td className="px-4 py-3 text-right">
                        <DiscountBadge value={row.avg_discount_pct} />
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {row.median_discount_pct.toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 text-right">
                        <TrendArrow delta={row.trend_delta} />
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500">
                        {row.sample_size.toLocaleString("pt-BR")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        <p className="mt-6 text-xs text-gray-400 text-center">
          Dados calculados mensalmente com base nos imóveis ativos monitorados pelo Radar Imóvel.
        </p>
      </div>
    </main>
  );
}
