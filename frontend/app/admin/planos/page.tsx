"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { FEATURE_LABELS } from "@/lib/entitlements";

interface Plan {
  id: string;
  code: string;
  name: string;
  price_brl: number;
  features: Record<string, boolean>;
  limits: Record<string, number>;
  active: boolean;
}

interface Catalog {
  features: { key: string; description: string }[];
  quotas: { key: string; period: string; description: string }[];
}

function formatPrice(cents: number) {
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function PlanosPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Plan | null>(null);

  const { data: plans = [], isLoading } = useQuery<Plan[]>({
    queryKey: ["admin", "plans"],
    queryFn: () => api.get("/admin/plans").then((r) => r.data),
  });

  const { data: catalog } = useQuery<Catalog>({
    queryKey: ["admin", "plans", "catalog"],
    queryFn: () => api.get("/admin/plans/catalog").then((r) => r.data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Plan> }) =>
      api.patch(`/admin/plans/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "plans"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      setEditing(null);
    },
  });

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5">
        <h1 className="text-lg font-semibold text-white">Planos</h1>
        <p className="text-xs text-gray-500 mt-0.5">Gerencie features e limites por plano</p>
      </div>

      <div className="px-8 py-6 max-w-5xl">
        {isLoading ? (
          <p className="text-gray-500 text-sm">Carregando...</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {plans.map((plan) => (
              <div key={plan.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-white font-semibold">{plan.name}</h2>
                    <p className="text-sm text-gray-400">{formatPrice(plan.price_brl)}/mês</p>
                  </div>
                  <button
                    onClick={() => setEditing(plan)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Editar
                  </button>
                </div>

                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Features</p>
                  <ul className="space-y-1">
                    {catalog?.features.map((f) => (
                      <li key={f.key} className="flex items-center gap-2 text-xs">
                        <span className={plan.features[f.key] ? "text-emerald-400" : "text-gray-600"}>
                          {plan.features[f.key] ? "✓" : "✗"}
                        </span>
                        <span className={plan.features[f.key] ? "text-gray-300" : "text-gray-600"}>
                          {f.description}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Limites</p>
                  <ul className="space-y-1">
                    {catalog?.quotas.map((q) => (
                      <li key={q.key} className="flex justify-between text-xs text-gray-400">
                        <span>{q.description}</span>
                        <span className="font-mono text-white">
                          {plan.limits[q.key] ?? "—"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <PlanEditModal
          plan={editing}
          catalog={catalog}
          onClose={() => setEditing(null)}
          onSave={(body) => updateMutation.mutate({ id: editing.id, body })}
          saving={updateMutation.isPending}
        />
      )}
    </div>
  );
}

function PlanEditModal({
  plan,
  catalog,
  onClose,
  onSave,
  saving,
}: {
  plan: Plan;
  catalog: Catalog | undefined;
  onClose: () => void;
  onSave: (body: Partial<Plan>) => void;
  saving: boolean;
}) {
  const [features, setFeatures] = useState<Record<string, boolean>>({ ...plan.features });
  const [limits, setLimits] = useState<Record<string, number>>({ ...plan.limits });
  const [price, setPrice] = useState(plan.price_brl);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg p-6 space-y-5">
        <h2 className="text-white font-semibold">Editar plano: {plan.name}</h2>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Preço (centavos)</label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
          />
          <p className="text-xs text-gray-600 mt-0.5">{formatPrice(price)}</p>
        </div>

        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Features</p>
          <div className="space-y-2">
            {catalog?.features.map((f) => (
              <label key={f.key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={features[f.key] ?? false}
                  onChange={(e) => setFeatures((prev) => ({ ...prev, [f.key]: e.target.checked }))}
                  className="rounded border-gray-600 bg-gray-800 text-blue-500"
                />
                <span className="text-sm text-gray-300">{f.description}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Limites</p>
          <div className="space-y-2">
            {catalog?.quotas.map((q) => (
              <div key={q.key} className="flex items-center gap-3">
                <label className="text-sm text-gray-400 flex-1">{q.description}</label>
                <input
                  type="number"
                  value={limits[q.key] ?? 0}
                  onChange={(e) => setLimits((prev) => ({ ...prev, [q.key]: Number(e.target.value) }))}
                  className="w-24 bg-gray-800 border border-gray-700 text-white rounded-lg px-2 py-1 text-sm font-mono"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={() => onSave({ features, limits, price_brl: price })}
            disabled={saving}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
          >
            {saving ? "Salvando..." : "Salvar"}
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
