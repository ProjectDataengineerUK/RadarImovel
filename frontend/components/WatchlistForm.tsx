"use client";

import { useState } from "react";
import type { Watchlist } from "@/lib/types";

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO",
  "MA","MG","MS","MT","PA","PB","PE","PI","PR",
  "RJ","RN","RO","RR","RS","SC","SE","SP","TO",
];

type WatchlistDraft = Omit<Watchlist, "id" | "user_id" | "active" | "created_at">;

interface WatchlistFormProps {
  initial?: Partial<WatchlistDraft>;
  onSubmit: (data: WatchlistDraft) => Promise<void>;
  onCancel: () => void;
}

export default function WatchlistForm({ initial = {}, onSubmit, onCancel }: WatchlistFormProps) {
  const [state, setState] = useState(initial.state ?? "");
  const [city, setCity] = useState(initial.city ?? "");
  const [maxPrice, setMaxPrice] = useState(initial.max_price ? String(initial.max_price) : "");
  const [minDiscount, setMinDiscount] = useState(initial.min_discount ? String(initial.min_discount) : "");
  const [propertyType, setPropertyType] = useState(initial.property_type ?? "");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit({
        state: state || null,
        city: city || null,
        max_price: maxPrice ? Number(maxPrice) : null,
        min_discount: minDiscount ? Number(minDiscount) : null,
        property_type: propertyType || null,
        bank_id: null,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">UF</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">Qualquer</option>
            {UFS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Cidade</label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Ex: Goiânia"
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preço máximo (R$)</label>
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            placeholder="Ex: 300000"
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Desconto mínimo (%)</label>
          <input
            type="number"
            value={minDiscount}
            onChange={(e) => setMinDiscount(e.target.value)}
            placeholder="Ex: 20"
            min={0}
            max={100}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de imóvel</label>
          <select
            value={propertyType}
            onChange={(e) => setPropertyType(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">Qualquer</option>
            <option value="Apartamento">Apartamento</option>
            <option value="Casa">Casa</option>
            <option value="Terreno">Terreno</option>
            <option value="Comercial">Comercial</option>
          </select>
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Salvando..." : "Salvar alerta"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border rounded text-sm hover:bg-gray-50"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
