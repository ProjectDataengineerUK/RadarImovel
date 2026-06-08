"use client";

import { useState } from "react";
import Link from "next/link";
import { useProperties } from "@/hooks/useProperties";
import { formatCurrency } from "@/lib/utils";
import ScoreBadge from "@/components/ScoreBadge";
import type { PropertyFilters as Filters } from "@/lib/types";

const STATES = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const TYPES = ["Apartamento","Casa","Terreno","Comercial","Rural","Outros"];
const MODALITIES = ["Licitação Aberta","Leilão","Venda Direta"];

export default function ImoveisPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(0);
  const [showFilters, setShowFilters] = useState(true);
  const { data, isLoading } = useProperties(filters, page);

  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const totalPages = Math.ceil(total / 50);

  const set = (key: keyof Filters, val: string) => {
    setFilters((f) => ({ ...f, [key]: val || undefined }));
    setPage(0);
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-800 px-8 py-5 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold text-white">Imóveis</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {isLoading ? "Carregando..." : `${total.toLocaleString("pt-BR")} imóveis encontrados`}
          </p>
        </div>
        <button
          onClick={() => setShowFilters((v) => !v)}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white border border-gray-800 hover:border-gray-700 rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
          </svg>
          {showFilters ? "Ocultar filtros" : "Filtros"}
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Filters */}
        {showFilters && (
          <aside className="w-56 border-r border-gray-800 bg-gray-900 px-4 py-5 overflow-y-auto shrink-0 space-y-5">
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Estado</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                value={filters.state ?? ""}
                onChange={(e) => set("state", e.target.value)}
              >
                <option value="">Todos</option>
                {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Cidade</label>
              <input
                type="text"
                placeholder="Qualquer cidade"
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm placeholder-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                value={filters.city ?? ""}
                onChange={(e) => set("city", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Tipo</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                value={filters.occupancy_status ?? ""}
                onChange={(e) => set("occupancy_status", e.target.value)}
              >
                <option value="">Todos</option>
                <option value="Desocupado">Desocupado</option>
                <option value="Ocupado">Ocupado</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Tipo de imóvel</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                onChange={(e) => set("sale_modality", e.target.value)}
              >
                <option value="">Todas modalidades</option>
                {MODALITIES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Preço máximo</label>
              <input
                type="number"
                placeholder="R$ ilimitado"
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm placeholder-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                value={filters.max_price ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, max_price: e.target.value ? Number(e.target.value) : undefined }))}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Desconto mínimo</label>
              <input
                type="number"
                placeholder="0%"
                min={0}
                max={100}
                className="w-full bg-gray-800 border border-gray-700 text-white text-sm placeholder-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
                value={filters.min_discount ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, min_discount: e.target.value ? Number(e.target.value) : undefined }))}
              />
            </div>

            <button
              onClick={() => { setFilters({}); setPage(0); }}
              className="w-full text-xs text-gray-500 hover:text-gray-300 transition-colors py-1"
            >
              Limpar filtros
            </button>
          </aside>
        )}

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-sm text-gray-500">
              Nenhum imóvel encontrado com esses filtros.
            </div>
          ) : (
            <>
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-950 z-10">
                  <tr className="border-b border-gray-800 text-left">
                    <th className="pl-6 pr-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                    <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Imóvel</th>
                    <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</th>
                    <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Modalidade</th>
                    <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Valor</th>
                    <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Desconto</th>
                    <th className="pl-4 pr-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Ocupação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {items.map((p) => (
                    <tr key={p.id} className="hover:bg-gray-900/60 transition-colors group">
                      <td className="pl-6 pr-4 py-3.5">
                        <ScoreBadge score={p.opportunity_score} />
                      </td>
                      <td className="px-4 py-3.5">
                        <Link href={`/imoveis/${p.id}`} className="font-medium text-white group-hover:text-blue-400 transition-colors">
                          {p.city}, {p.state}
                        </Link>
                        {p.neighborhood && <p className="text-xs text-gray-500 mt-0.5">{p.neighborhood}</p>}
                      </td>
                      <td className="px-4 py-3.5 text-gray-400">{p.property_type}</td>
                      <td className="px-4 py-3.5 text-gray-400">{p.sale_modality}</td>
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

              {/* Pagination */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-gray-800">
                <p className="text-xs text-gray-500">
                  Página {page + 1} de {totalPages || 1} · {total.toLocaleString("pt-BR")} imóveis
                </p>
                <div className="flex items-center gap-2">
                  <button
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                    className="px-3 py-1.5 text-xs text-gray-400 border border-gray-800 rounded-lg hover:border-gray-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Anterior
                  </button>
                  <button
                    disabled={!data || (page + 1) * 50 >= total}
                    onClick={() => setPage((p) => p + 1)}
                    className="px-3 py-1.5 text-xs text-gray-400 border border-gray-800 rounded-lg hover:border-gray-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Próximo →
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
