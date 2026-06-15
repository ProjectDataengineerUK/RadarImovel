"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useRiskHeatmap } from "@/hooks/useRisk";
import { FeatureGate } from "@/components/FeatureGate";
import type { Property, PaginatedResponse } from "@/lib/types";

const RiskMap = dynamic(
  () => import("@/components/RiskMap").then((m) => m.RiskMap),
  { ssr: false, loading: () => <div className="h-full w-full animate-pulse bg-gray-100 rounded-lg" /> }
);

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG",
  "MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR",
  "RS","SC","SE","SP","TO",
];

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

export default function MapaPage() {
  return (
    <FeatureGate feature="risk_score">
      <MapaContent />
    </FeatureGate>
  );
}

function MapaContent() {
  const [uf, setUf] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<{ city: string; state: string } | null>(null);
  const { data, isLoading } = useRiskHeatmap(uf);

  const handleCityClick = useCallback((city: string, state: string) => {
    setSelected({ city, state });
  }, []);

  const cityQuery = useQuery<PaginatedResponse<Property>>({
    queryKey: ["map-city-props", selected?.city, selected?.state],
    queryFn: () =>
      api.get("/properties", {
        params: { city: selected!.city, state: selected!.state, limit: 10, status: "active" },
      }).then((r) => r.data),
    enabled: !!selected,
  });

  const cityProps = cityQuery.data?.items ?? [];

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* Left sidebar — filters + legend */}
      <aside className="w-56 shrink-0 border-r bg-white p-4 space-y-4 overflow-y-auto text-gray-900">
        <h1 className="text-lg font-bold text-gray-900">Mapa de Risco</h1>

        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Estado</label>
          <select
            className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm text-gray-900 bg-white"
            value={uf ?? ""}
            onChange={(e) => { setUf(e.target.value || undefined); setSelected(null); }}
          >
            <option value="">Todos</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Legenda</p>
          {[
            { label: "Baixo (0–20)", color: "#22c55e" },
            { label: "Moderado (21–40)", color: "#eab308" },
            { label: "Elevado (41–60)", color: "#f97316" },
            { label: "Alto (61–80)", color: "#ef4444" },
            { label: "Crítico (81–100)", color: "#18181b" },
          ].map(({ label, color }) => (
            <div key={label} className="flex items-center gap-2 text-sm">
              <span className="inline-block h-3 w-3 rounded-full" style={{ background: color }} />
              {label}
            </div>
          ))}
        </div>

        <div className="pt-2 border-t">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">2ª Praça</p>
          <div className="flex items-center gap-2 text-xs text-red-700 bg-red-50 rounded px-2 py-1.5 border border-red-200">
            <span className="inline-block h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            Deságio ≥40% — oportunidade P0
          </div>
        </div>

        {data && (
          <p className="text-xs text-gray-400">{data.features.length} municípios com dados</p>
        )}
      </aside>

      {/* Map */}
      <main className="flex-1 relative">
        {isLoading ? (
          <div className="h-full w-full animate-pulse rounded-xl bg-gray-100" />
        ) : (
          <RiskMap features={data?.features ?? []} onCityClick={handleCityClick} />
        )}
      </main>

      {/* Right sidebar — properties of clicked city */}
      {selected && (
        <aside className="w-80 shrink-0 border-l bg-white flex flex-col text-gray-900">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <div>
              <p className="font-semibold text-sm">{selected.city} / {selected.state}</p>
              <p className="text-xs text-gray-400">
                {cityQuery.isLoading ? "Carregando..." : `${cityProps.length} imóveis`}
              </p>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            >
              ×
            </button>
          </div>

          <div className="overflow-y-auto flex-1 divide-y">
            {cityQuery.isLoading && (
              <div className="p-4 space-y-3 animate-pulse">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded" />
                ))}
              </div>
            )}

            {!cityQuery.isLoading && cityProps.length === 0 && (
              <p className="p-4 text-sm text-gray-500">Nenhum imóvel ativo encontrado.</p>
            )}

            {cityProps.map((p) => (
              <a
                key={p.id}
                href={`/imoveis/${p.id}`}
                className="block px-4 py-3 hover:bg-gray-50 transition"
              >
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  {p.property_type}
                  {p.sale_modality ? ` · ${p.sale_modality}` : ""}
                </p>
                <p className="text-sm text-gray-800 mt-0.5 line-clamp-1">
                  {p.address ?? p.neighborhood ?? p.city}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-sm font-bold text-blue-700">{fmt(p.current_value)}</span>
                  {p.discount_percent != null && (
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      p.discount_percent >= 40
                        ? "bg-green-100 text-green-800"
                        : p.discount_percent >= 20
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-gray-100 text-gray-600"
                    }`}>
                      -{p.discount_percent.toFixed(0)}%
                    </span>
                  )}
                  {p.risk_level && (
                    <span className="text-xs text-gray-400">Risco: {p.risk_level}</span>
                  )}
                </div>
              </a>
            ))}
          </div>

          {cityProps.length === 10 && (
            <div className="border-t px-4 py-3">
              <a
                href={`/imoveis?city=${encodeURIComponent(selected.city)}&state=${selected.state}`}
                className="block text-center text-xs text-blue-600 hover:underline"
              >
                Ver todos os imóveis de {selected.city} →
              </a>
            </div>
          )}
        </aside>
      )}
    </div>
  );
}
