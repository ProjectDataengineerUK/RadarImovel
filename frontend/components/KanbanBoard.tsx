"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export interface PortfolioItem {
  id: string;
  property_id: string;
  stage: string;
  actual_purchase_price: number | null;
  actual_renovation_cost: number | null;
  actual_other_costs: number | null;
  notes: string | null;
  updated_at: string;
  property?: {
    city: string;
    state: string;
    current_value: number;
    property_type: string;
    opportunity_score: number | null;
  };
}

const STAGES = [
  { key: "monitorando", label: "Monitorando", color: "bg-blue-100 border-blue-300" },
  { key: "analisando", label: "Analisando", color: "bg-yellow-100 border-yellow-300" },
  { key: "proposta", label: "Proposta", color: "bg-orange-100 border-orange-300" },
  { key: "arrematado", label: "Arrematado", color: "bg-green-100 border-green-300" },
  { key: "descartado", label: "Descartado", color: "bg-gray-100 border-gray-300" },
];

const R$ = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function Card({ item, onMove, onRemove }: { item: PortfolioItem; onMove: (s: string) => void; onRemove: () => void }) {
  const p = item.property;
  return (
    <div className="bg-white rounded-lg shadow-sm border p-3 mb-2 text-sm">
      <div className="flex justify-between items-start mb-1">
        <span className="font-medium text-gray-800 truncate">
          {p ? `${p.city}/${p.state}` : item.property_id.slice(0, 8)}
        </span>
        <button onClick={onRemove} className="text-gray-300 hover:text-red-400 text-xs ml-2">✕</button>
      </div>
      {p && (
        <>
          <p className="text-gray-500 text-xs">{p.property_type}</p>
          <p className="text-blue-700 font-semibold">{R$(p.current_value)}</p>
          {p.opportunity_score !== null && (
            <p className="text-xs text-gray-400">Score {p.opportunity_score}</p>
          )}
        </>
      )}
      {item.actual_purchase_price && (
        <p className="text-xs text-green-700 mt-1">Comprado: {R$(item.actual_purchase_price)}</p>
      )}
      {item.notes && <p className="text-xs text-gray-400 mt-1 truncate" title={item.notes}>{item.notes}</p>}

      <select
        value={item.stage}
        onChange={(e) => onMove(e.target.value)}
        className="mt-2 w-full text-xs border rounded px-1 py-1 focus:outline-none"
      >
        {STAGES.map((s) => (
          <option key={s.key} value={s.key}>{s.label}</option>
        ))}
      </select>
    </div>
  );
}

interface Props {
  items: PortfolioItem[];
}

export function KanbanBoard({ items }: Props) {
  const qc = useQueryClient();

  const moveMutation = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) =>
      api.patch(`/portfolio/${id}`, { stage }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/portfolio/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });

  const byStage = STAGES.reduce<Record<string, PortfolioItem[]>>((acc, s) => {
    acc[s.key] = items.filter((i) => i.stage === s.key);
    return acc;
  }, {});

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {STAGES.map((stage) => (
        <div key={stage.key} className={`min-w-[220px] rounded-lg border-2 ${stage.color} p-3`}>
          <h3 className="font-semibold text-gray-700 mb-3 text-sm flex justify-between">
            {stage.label}
            <span className="bg-white text-gray-500 text-xs rounded-full px-2 py-0.5">{byStage[stage.key].length}</span>
          </h3>
          {byStage[stage.key].map((item) => (
            <Card
              key={item.id}
              item={item}
              onMove={(s) => moveMutation.mutate({ id: item.id, stage: s })}
              onRemove={() => removeMutation.mutate(item.id)}
            />
          ))}
          {byStage[stage.key].length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">Vazio</p>
          )}
        </div>
      ))}
    </div>
  );
}
