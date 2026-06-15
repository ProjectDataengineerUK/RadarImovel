"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

interface Plan {
  id: string;
  code: string;
  name: string;
  price_brl: number;
  active: boolean;
}

const ROLES = ["user", "suporte", "operador", "admin"];

export default function NovoUsuarioPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    name: "",
    role: "user",
    plan_code: "free",
    expires_days: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const { data: plans = [] } = useQuery<Plan[]>({
    queryKey: ["admin", "plans"],
    queryFn: () => api.get("/admin/plans").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (body: typeof form) =>
      api.post("/admin/users", {
        email: body.email,
        name: body.name || undefined,
        role: body.role,
        plan_code: body.plan_code,
        expires_days: body.expires_days ? Number(body.expires_days) : undefined,
        notes: body.notes || undefined,
      }),
    onSuccess: () => {
      router.push("/admin/usuarios");
    },
    onError: (e: any) => {
      setError(e?.response?.data?.detail ?? "Erro ao criar usuário");
    },
  });

  const activePlans = plans.filter((p) => p.active);

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5 flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
        >
          ← Voltar
        </button>
        <div>
          <h1 className="text-lg font-semibold text-white">Novo Usuário</h1>
          <p className="text-xs text-gray-500 mt-0.5">Cadastro manual de acesso ao sistema</p>
        </div>
      </div>

      <div className="px-8 py-8 max-w-lg">
        {error && (
          <div className="mb-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">E-mail *</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="usuario@empresa.com.br"
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Nome (opcional)</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="João da Silva"
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Papel</label>
              <select
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Plano</label>
              <select
                value={form.plan_code}
                onChange={(e) => setForm((f) => ({ ...f, plan_code: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {activePlans.map((p) => (
                  <option key={p.code} value={p.code}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Duração (dias) — deixe em branco para acesso permanente</label>
            <input
              type="number"
              value={form.expires_days}
              onChange={(e) => setForm((f) => ({ ...f, expires_days: e.target.value }))}
              placeholder="30"
              min="1"
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Observações internas (opcional)</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              rows={3}
              placeholder="Cliente referenciado por parceiro X, trial B2B..."
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>

          <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg px-4 py-3 text-xs text-blue-300">
            O usuário receberá um e-mail para definir sua senha ao fazer o primeiro login com Google ou ao usar o link de convite.
          </div>

          <div className="flex gap-3 pt-1">
            <button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.email || createMutation.isPending}
              className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
            >
              {createMutation.isPending ? "Criando..." : "Criar usuário"}
            </button>
            <button
              onClick={() => router.back()}
              className="flex-1 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
