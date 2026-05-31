"use client";

import { useState } from "react";
import { useProperties } from "@/hooks/useProperties";
import PropertyTable from "@/components/PropertyTable";
import PropertyFilters from "@/components/PropertyFilters";
import type { PropertyFilters as Filters } from "@/lib/types";

export default function ImoveisPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(0);
  const { data, isLoading } = useProperties(filters, page);

  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r p-4 overflow-y-auto">
        <PropertyFilters value={filters} onChange={(f) => { setFilters(f); setPage(0); }} />
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <h1 className="text-2xl font-bold mb-4">Imóveis</h1>
        {isLoading ? (
          <p>Carregando...</p>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">{data?.total ?? 0} imóveis encontrados</p>
            <PropertyTable properties={data?.items ?? []} />
            <div className="flex gap-2 mt-4">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 border rounded disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                disabled={!data || (page + 1) * 50 >= data.total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 border rounded disabled:opacity-40"
              >
                Próximo
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
