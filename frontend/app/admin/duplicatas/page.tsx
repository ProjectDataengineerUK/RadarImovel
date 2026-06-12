"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";

interface DuplicateItem {
  id: string;
  title: string | null;
  city: string;
  state: string;
  current_value: number;
  official_url: string;
  possible_duplicate_of: string;
  first_seen_at: string;
}

export default function DuplicatasPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<{ a: DuplicateItem; b: DuplicateItem } | null>(null);

  const { data: duplicates = [], isLoading } = useQuery<DuplicateItem[]>({
    queryKey: ["admin", "dedup"],
    queryFn: () => api.get("/admin/dedup").then((r) => r.data),
  });

  const mergeMutation = useMutation({
    mutationFn: (body: { keep_id: string; discard_id: string }) =>
      api.post("/admin/dedup/merge", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "dedup"] });
      setSelected(null);
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (propertyId: string) =>
      api.delete(`/admin/dedup/${propertyId}/flag`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "dedup"] }),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Carregando...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/admin" className="text-sm text-blue-600 hover:underline">← Admin</Link>
          <h1 className="text-2xl font-bold mt-1">Fila de Duplicatas</h1>
          <p className="text-sm text-gray-500 mt-1">
            {duplicates.length} imóveis aguardando revisão
          </p>
        </div>
      </div>

      {duplicates.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          Nenhuma duplicata pendente. Bom trabalho!
        </div>
      )}

      <div className="divide-y rounded-lg border overflow-hidden bg-white">
        {duplicates.map((item) => (
          <DuplicateRow
            key={item.id}
            item={item}
            onDismiss={() => dismissMutation.mutate(item.id)}
            onReview={() => {
              const original = duplicates.find((d) => d.id === item.possible_duplicate_of);
              if (original) setSelected({ a: original, b: item });
            }}
          />
        ))}
      </div>

      {selected && (
        <MergeModal
          a={selected.a}
          b={selected.b}
          onMerge={(keepId, discardId) => mergeMutation.mutate({ keep_id: keepId, discard_id: discardId })}
          onClose={() => setSelected(null)}
          loading={mergeMutation.isPending}
        />
      )}
    </div>
  );
}

function DuplicateRow({
  item,
  onDismiss,
  onReview,
}: {
  item: DuplicateItem;
  onDismiss: () => void;
  onReview: () => void;
}) {
  return (
    <div className="p-4 flex items-start justify-between gap-4">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">
          {item.title ?? `Imóvel em ${item.city}/${item.state}`}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {formatCurrency(item.current_value)} · {item.city}/{item.state} ·{" "}
          detectado {formatDate(item.first_seen_at)}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Possível duplicata de:{" "}
          <span className="font-mono text-gray-600">{item.possible_duplicate_of.slice(0, 8)}…</span>
        </p>
      </div>
      <div className="flex gap-2 shrink-0">
        <button
          onClick={onReview}
          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Revisar
        </button>
        <button
          onClick={onDismiss}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded hover:bg-gray-50"
        >
          Falso positivo
        </button>
      </div>
    </div>
  );
}

function MergeModal({
  a,
  b,
  onMerge,
  onClose,
  loading,
}: {
  a: DuplicateItem;
  b: DuplicateItem;
  onMerge: (keepId: string, discardId: string) => void;
  onClose: () => void;
  loading: boolean;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 max-w-2xl w-full mx-4 space-y-4">
        <h2 className="text-lg font-semibold">Confirmar mesclagem</h2>
        <p className="text-sm text-gray-500">
          Selecione qual registro manter. As ofertas do descartado serão movidas para o mantido.
        </p>
        <div className="grid grid-cols-2 gap-4">
          {[a, b].map((item) => (
            <div key={item.id} className="border rounded-lg p-4 space-y-2">
              <p className="font-medium text-sm">{item.title ?? `${item.city}/${item.state}`}</p>
              <p className="text-xs text-gray-500">{formatCurrency(item.current_value)}</p>
              <p className="text-xs text-gray-400 font-mono">{item.id.slice(0, 8)}…</p>
              <a
                href={item.official_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline"
              >
                Ver no site →
              </a>
              <button
                onClick={() => onMerge(item.id, item.id === a.id ? b.id : a.id)}
                disabled={loading}
                className="w-full mt-2 px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                Manter este
              </button>
            </div>
          ))}
        </div>
        <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700 w-full text-center">
          Cancelar
        </button>
      </div>
    </div>
  );
}
