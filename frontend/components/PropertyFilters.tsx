"use client";

import type { PropertyFilters } from "@/lib/types";

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO",
  "MA","MG","MS","MT","PA","PB","PE","PI","PR",
  "RJ","RN","RO","RR","RS","SC","SE","SP","TO",
];

interface PropertyFiltersProps {
  value: PropertyFilters;
  onChange: (f: PropertyFilters) => void;
}

export default function PropertyFiltersComponent({ value, onChange }: PropertyFiltersProps) {
  function set(key: keyof PropertyFilters, raw: string) {
    const numericKeys = ["max_price", "min_discount"] as const;
    const v = numericKeys.includes(key as any) ? (raw ? Number(raw) : undefined) : (raw || undefined);
    onChange({ ...value, [key]: v });
  }

  function reset() {
    onChange({});
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm text-gray-700">Filtros</h3>
        <button onClick={reset} className="text-xs text-blue-600 hover:underline">Limpar</button>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">UF</label>
        <select
          value={value.state ?? ""}
          onChange={(e) => set("state", e.target.value)}
          className="w-full border rounded px-2 py-1.5 text-sm"
        >
          <option value="">Todas</option>
          {UFS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Cidade</label>
        <input
          type="text"
          placeholder="Ex: Goiânia"
          value={value.city ?? ""}
          onChange={(e) => set("city", e.target.value)}
          className="w-full border rounded px-2 py-1.5 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Preço máximo (R$)</label>
        <input
          type="number"
          placeholder="Ex: 300000"
          value={value.max_price ?? ""}
          onChange={(e) => set("max_price", e.target.value)}
          className="w-full border rounded px-2 py-1.5 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Desconto mínimo (%)</label>
        <input
          type="number"
          placeholder="Ex: 20"
          min={0}
          max={100}
          value={value.min_discount ?? ""}
          onChange={(e) => set("min_discount", e.target.value)}
          className="w-full border rounded px-2 py-1.5 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Situação</label>
        <select
          value={value.occupancy_status ?? ""}
          onChange={(e) => set("occupancy_status", e.target.value)}
          className="w-full border rounded px-2 py-1.5 text-sm"
        >
          <option value="">Todas</option>
          <option value="Desocupado">Desocupado</option>
          <option value="Ocupado">Ocupado</option>
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Modalidade</label>
        <select
          value={value.sale_modality ?? ""}
          onChange={(e) => set("sale_modality", e.target.value)}
          className="w-full border rounded px-2 py-1.5 text-sm"
        >
          <option value="">Todas</option>
          <option value="Licitação Aberta">Licitação Aberta</option>
          <option value="Venda Direta">Venda Direta</option>
          <option value="Leilão SFI">Leilão SFI</option>
          <option value="Leilão SFH">Leilão SFH</option>
        </select>
      </div>
    </div>
  );
}
