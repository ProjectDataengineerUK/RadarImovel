"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Watchlist } from "@/lib/types";
import WatchlistForm from "@/components/WatchlistForm";

export default function AlertasPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data: watchlists = [], isLoading } = useQuery<Watchlist[]>({
    queryKey: ["watchlists"],
    queryFn: () => api.get("/watchlists").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: Omit<Watchlist, "id" | "user_id" | "active" | "created_at">) =>
      api.post("/watchlists", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlists"] });
      setShowForm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/watchlists/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api.patch(`/watchlists/${id}`, { active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });

  const editing = watchlists.find((w) => w.id === editingId);

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Alertas</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); }}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
        >
          + Novo alerta
        </button>
      </div>

      {(showForm && !editingId) && (
        <div className="border rounded-lg p-6 bg-gray-50">
          <h2 className="font-semibold mb-4">Novo alerta</h2>
          <WatchlistForm
            onSubmit={async (data) => { await createMutation.mutateAsync(data); }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-500">Carregando alertas...</p>
      ) : watchlists.length === 0 ? (
        <p className="text-gray-400 text-center py-12">Nenhum alerta configurado ainda.</p>
      ) : (
        <div className="space-y-3">
          {watchlists.map((w) => (
            <div key={w.id} className="border rounded-lg p-4 bg-white">
              {editingId === w.id ? (
                <WatchlistForm
                  initial={w}
                  onSubmit={async (data) => {
                    await api.put(`/watchlists/${w.id}`, data);
                    qc.invalidateQueries({ queryKey: ["watchlists"] });
                    setEditingId(null);
                  }}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <WatchlistSummary watchlist={w} />
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => toggleMutation.mutate({ id: w.id, active: !w.active })}
                      className={`text-xs px-2 py-1 rounded border ${w.active ? "bg-green-50 text-green-700 border-green-200" : "bg-gray-50 text-gray-400 border-gray-200"}`}
                    >
                      {w.active ? "Ativo" : "Pausado"}
                    </button>
                    <button onClick={() => setEditingId(w.id)} className="text-xs text-blue-600 hover:underline">Editar</button>
                    <button onClick={() => deleteMutation.mutate(w.id)} className="text-xs text-red-500 hover:underline">Remover</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WatchlistSummary({ watchlist: w }: { watchlist: Watchlist }) {
  const parts = [
    w.state && `UF: ${w.state}`,
    w.city && `Cidade: ${w.city}`,
    w.max_price && `Máx: R$ ${w.max_price.toLocaleString("pt-BR")}`,
    w.min_discount && `Desconto ≥ ${w.min_discount}%`,
    w.property_type && w.property_type,
  ].filter(Boolean);

  return (
    <p className="text-sm text-gray-700">{parts.length > 0 ? parts.join(" · ") : "Todos os imóveis"}</p>
  );
}
