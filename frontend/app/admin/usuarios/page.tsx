"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { PLAN_DISPLAY } from "@/lib/entitlements";
import { formatDate } from "@/lib/utils";

interface AdminUser {
  id: string;
  email: string;
  role: string;
  plan: string;
  telegram_connected: boolean;
  created_at: string;
}

interface UserList {
  total: number;
  items: AdminUser[];
}

const ROLES = ["user", "suporte", "operador", "admin"];
const PLANS = ["free", "pro", "premium"];

export default function UsuariosPage() {
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<AdminUser | null>(null);

  const { data, isLoading } = useQuery<UserList>({
    queryKey: ["admin", "users", offset],
    queryFn: () => api.get("/admin/users", { params: { offset, limit: 50 } }).then((r) => r.data),
  });

  const assignPlan = useMutation({
    mutationFn: ({ userId, plan_code }: { userId: string; plan_code: string }) =>
      api.post(`/admin/users/${userId}/plan`, { plan_code }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const setRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.post(`/admin/users/${userId}/role`, { role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const limit = 50;
  const total = data?.total ?? 0;

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5">
        <h1 className="text-lg font-semibold text-white">Usuários</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          {total} usuários registrados
        </p>
      </div>

      <div className="px-8 py-6 max-w-5xl">
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {["E-mail", "Plano", "Papel", "Telegram", "Cadastro"].map((h) => (
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
                data?.items.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-800/50 cursor-pointer" onClick={() => setSelected(user)}>
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs">{user.email}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium ${PLAN_DISPLAY[user.plan]?.color ?? "text-gray-400"}`}>
                        {PLAN_DISPLAY[user.plan]?.label ?? user.plan}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{user.role}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs ${user.telegram_connected ? "text-emerald-400" : "text-gray-600"}`}>
                        {user.telegram_connected ? "Conectado" : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{formatDate(user.created_at)}</td>
                  </tr>
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

      {selected && (
        <UserActionModal
          user={selected}
          onClose={() => setSelected(null)}
          onAssignPlan={(plan_code) => {
            assignPlan.mutate({ userId: selected.id, plan_code });
            setSelected(null);
          }}
          onSetRole={(role) => {
            setRole.mutate({ userId: selected.id, role });
            setSelected(null);
          }}
        />
      )}
    </div>
  );
}

function UserActionModal({
  user,
  onClose,
  onAssignPlan,
  onSetRole,
}: {
  user: AdminUser;
  onClose: () => void;
  onAssignPlan: (plan: string) => void;
  onSetRole: (role: string) => void;
}) {
  const [plan, setPlan] = useState(user.plan);
  const [role, setRole] = useState(user.role);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-md p-6 space-y-5">
        <h2 className="text-white font-semibold truncate">{user.email}</h2>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Plano</label>
            <select
              value={plan}
              onChange={(e) => setPlan(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
            >
              {PLANS.map((p) => (
                <option key={p} value={p}>{PLAN_DISPLAY[p]?.label ?? p}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Papel</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => {
              if (plan !== user.plan) onAssignPlan(plan);
              if (role !== user.role) onSetRole(role);
              if (plan === user.plan && role === user.role) onClose();
            }}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Aplicar
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
