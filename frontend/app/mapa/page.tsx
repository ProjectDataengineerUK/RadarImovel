"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useRiskHeatmap } from "@/hooks/useRisk";
import { FeatureGate } from "@/components/FeatureGate";

const RiskMap = dynamic(
  () => import("@/components/RiskMap").then((m) => m.RiskMap),
  { ssr: false, loading: () => <div className="h-full w-full animate-pulse bg-gray-100 rounded-lg" /> }
);

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG",
  "MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR",
  "RS","SC","SE","SP","TO",
];

export default function MapaPage() {
  return (
    <FeatureGate feature="risk_score">
      <MapaContent />
    </FeatureGate>
  );
}

function MapaContent() {
  const [uf, setUf] = useState<string | undefined>(undefined);
  const { data, isLoading } = useRiskHeatmap(uf);

  return (
    <div className="flex h-[calc(100vh-64px)]">
      <aside className="w-64 shrink-0 border-r bg-white p-4 space-y-4 overflow-y-auto">
        <h1 className="text-lg font-bold">Mapa de Risco</h1>

        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Estado</label>
          <select
            className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm"
            value={uf ?? ""}
            onChange={(e) => setUf(e.target.value || undefined)}
          >
            <option value="">Todos</option>
            {UFS.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
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

        {data && (
          <p className="text-xs text-gray-400">
            {data.features.length} municípios com dados
          </p>
        )}
      </aside>

      <main className="flex-1 p-4">
        {isLoading ? (
          <div className="h-full w-full animate-pulse rounded-xl bg-gray-100" />
        ) : (
          <RiskMap features={data?.features ?? []} />
        )}
      </main>
    </div>
  );
}
