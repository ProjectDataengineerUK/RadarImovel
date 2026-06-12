"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface AuditEntry {
  id: string;
  actor_user_id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
}

interface AuditList {
  total: number;
  items: AuditEntry[];
}

function ActionBadge({ action }: { action: string }) {
  const color = action.includes("create")
    ? "bg-emerald-500/10 text-emerald-400"
    : action.includes("delete")
    ? "bg-red-500/10 text-red-400"
    : "bg-blue-500/10 text-blue-400";
  return (
    <span className={`inline-flex text-xs font-mono px-2 py-0.5 rounded-full ${color}`}>
      {action}
    </span>
  );
}

export default function AuditoriaPage() {
  const [offset, setOffset] = useState(0);
  const [entityType, setEntityType] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading } = useQuery<AuditList>({
    queryKey: ["admin", "audit", offset, entityType],
    queryFn: () =>
      api
        .get("/admin/audit", { params: { offset, limit: 50, ...(entityType ? { entity_type: entityType } : {}) } })
        .then((r) => r.data),
  });

  const limit = 50;
  const total = data?.total ?? 0;

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white">Log de Auditoria</h1>
          <p className="text-xs text-gray-500 mt-0.5">{total} registros</p>
        </div>
        <select
          value={entityType}
          onChange={(e) => { setEntityType(e.target.value); setOffset(0); }}
          className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2"
        >
          <option value="">Todos os tipos</option>
          <option value="plan">plan</option>
          <option value="user">user</option>
        </select>
      </div>

      <div className="px-8 py-6 max-w-5xl">
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {["Data", "Ação", "Entidade", "ID", "Ator"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-600">
                    Carregando...
                  </td>
                </tr>
              ) : (
                data?.items.map((entry) => (
                  <>
                    <tr
                      key={entry.id}
                      className="hover:bg-gray-800/50 cursor-pointer"
                      onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                    >
                      <td className="px-4 py-3 text-gray-500 text-xs font-mono whitespace-nowrap">
                        {new Date(entry.created_at).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-4 py-3">
                        <ActionBadge action={entry.action} />
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{entry.entity_type}</td>
                      <td className="px-4 py-3 text-gray-600 text-xs font-mono truncate max-w-[120px]">
                        {entry.entity_id}
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs font-mono truncate max-w-[120px]">
                        {entry.actor_user_id}
                      </td>
                    </tr>
                    {expanded === entry.id && (entry.before || entry.after) && (
                      <tr key={`${entry.id}-detail`} className="bg-gray-800/30">
                        <td colSpan={5} className="px-6 py-3">
                          <div className="grid grid-cols-2 gap-4">
                            {entry.before && (
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Antes</p>
                                <pre className="text-xs text-gray-400 font-mono bg-gray-900 rounded p-2 overflow-auto max-h-32">
                                  {JSON.stringify(entry.before, null, 2)}
                                </pre>
                              </div>
                            )}
                            {entry.after && (
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Depois</p>
                                <pre className="text-xs text-gray-400 font-mono bg-gray-900 rounded p-2 overflow-auto max-h-32">
                                  {JSON.stringify(entry.after, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))
              )}
            </tbody>
          </table>

          {total > limit && (
            <div className="border-t border-gray-800 px-4 py-3 flex items-center justify-between">
              <p className="text-xs text-gray-500">
                {offset + 1}–{Math.min(offset + limit, total)} de {total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="text-xs px-3 py-1.5 bg-gray-800 text-gray-400 rounded-lg disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                  className="text-xs px-3 py-1.5 bg-gray-800 text-gray-400 rounded-lg disabled:opacity-40"
                >
                  Próximo
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
