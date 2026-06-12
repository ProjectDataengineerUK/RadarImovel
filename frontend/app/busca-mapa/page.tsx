"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { PaginatedResponse, Property } from "@/lib/types";

const SearchMap = dynamic(() => import("@/components/SearchMap"), { ssr: false });

interface MapFilters {
  state: string;
  city: string;
  max_price: string;
  min_discount: string;
  radius_km: number;
}

const DEFAULT_FILTERS: MapFilters = {
  state: "",
  city: "",
  max_price: "",
  min_discount: "",
  radius_km: 20,
};

export default function BuscaMapaPage() {
  const [filters, setFilters] = useState<MapFilters>(DEFAULT_FILTERS);
  const [applied, setApplied] = useState<MapFilters>(DEFAULT_FILTERS);
  const [center, setCenter] = useState<[number, number] | null>(null);

  const params: Record<string, string> = {};
  if (applied.state) params.state = applied.state;
  if (applied.city) params.city = applied.city;
  if (applied.max_price) params.max_price = applied.max_price;
  if (applied.min_discount) params.min_discount = applied.min_discount;

  const { data, isLoading } = useQuery<PaginatedResponse<Property>>({
    queryKey: ["map-properties", params],
    queryFn: () => api.get("/properties", { params: { ...params, limit: 200 } }).then((r) => r.data),
  });

  const properties = data?.items ?? [];

  const handleApply = useCallback(() => {
    setApplied({ ...filters });
  }, [filters]);

  return (
    <div className="h-screen flex flex-col">
      <header className="bg-white border-b px-4 py-3 flex gap-3 items-end flex-wrap z-10 relative">
        <h1 className="text-lg font-semibold text-gray-800 mr-4">Busca por Mapa</h1>

        <div className="flex gap-2 flex-wrap">
          {(["state", "city", "max_price", "min_discount"] as const).map((k) => (
            <input
              key={k}
              type="text"
              placeholder={{ state: "UF", city: "Cidade", max_price: "Preço máx (R$)", min_discount: "Desconto mín (%)" }[k]}
              value={filters[k]}
              onChange={(e) => setFilters((f) => ({ ...f, [k]: e.target.value }))}
              className="border rounded px-2 py-1 text-sm w-36 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          ))}
          <label className="flex items-center gap-1 text-sm text-gray-600">
            Raio
            <input
              type="number"
              min={1}
              max={200}
              value={filters.radius_km}
              onChange={(e) => setFilters((f) => ({ ...f, radius_km: Number(e.target.value) }))}
              className="border rounded px-2 py-1 w-16 text-sm"
            />
            km
          </label>
          <button
            onClick={handleApply}
            className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 transition"
          >
            Buscar
          </button>
        </div>

        {isLoading && <span className="text-sm text-gray-400">Carregando...</span>}
        {!isLoading && (
          <span className="text-sm text-gray-500 ml-auto">{properties.length} imóveis</span>
        )}
      </header>

      <div className="flex-1 relative">
        <SearchMap
          properties={properties}
          center={center}
          onCenterChange={setCenter}
          radiusKm={applied.radius_km}
        />
      </div>
    </div>
  );
}
