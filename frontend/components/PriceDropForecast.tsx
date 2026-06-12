"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface Prediction {
  horizon: number;
  probability: number;
  expected_drop_pct: number;
  model_version: string;
  basis: {
    bank_code: string;
    modality: string;
    empirical_n: number;
    blend_weight: number;
  };
}

async function fetchPredictions(id: string): Promise<Prediction[]> {
  const { data } = await api.get(`/properties/${id}/predictions`);
  return data;
}

function ProbBar({ probability, horizon }: { probability: number; horizon: number }) {
  const pct = Math.round(probability * 100);
  const color =
    pct >= 70 ? "bg-red-500" : pct >= 45 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-3">
      <span className="w-16 text-sm text-gray-500 text-right">{horizon}d</span>
      <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-sm font-semibold text-gray-700">{pct}%</span>
    </div>
  );
}

export function PriceDropForecast({ propertyId }: { propertyId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["predictions", propertyId],
    queryFn: () => fetchPredictions(propertyId),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="bg-white border rounded-xl p-4 space-y-2 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/2" />
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-full" />
      </div>
    );
  }

  if (isError || !data?.length) return null;

  const first = data[0];
  const basisN = first.basis?.empirical_n ?? 0;
  const blendLabel =
    basisN >= 30 ? `baseado em ${basisN} imóveis similares` : "baseado em histórico do banco";

  return (
    <div className="bg-white border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-lg">📉</span>
        <h3 className="font-semibold text-gray-800">Previsão de queda de preço</h3>
      </div>

      <p className="text-xs text-gray-400">{blendLabel}</p>

      <div className="space-y-2">
        {data.map((p) => (
          <ProbBar key={p.horizon} probability={p.probability} horizon={p.horizon} />
        ))}
      </div>

      <p className="text-xs text-gray-400 mt-1">
        Queda esperada:{" "}
        <span className="font-medium">
          {data[0]?.expected_drop_pct?.toFixed(1)}% (30d) /{" "}
          {data[1]?.expected_drop_pct?.toFixed(1)}% (60d)
        </span>
      </p>
    </div>
  );
}
