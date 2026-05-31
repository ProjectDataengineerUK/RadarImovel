"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { User } from "@/lib/types";
import TelegramConnect from "@/components/TelegramConnect";
import { useAuth } from "@/hooks/useAuth";

export default function ConfiguracoesPage() {
  const { user: firebaseUser, logout } = useAuth();

  const { data: me } = useQuery<User>({
    queryKey: ["me"],
    queryFn: () => api.get("/users/me").then((r) => r.data),
  });

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Configurações</h1>

      <section className="border rounded-lg p-6 space-y-3">
        <h2 className="font-semibold text-lg">Conta</h2>
        <div className="text-sm text-gray-600 space-y-1">
          <p><span className="text-gray-400">E-mail:</span> {firebaseUser?.email ?? "—"}</p>
          <p><span className="text-gray-400">Conta criada em:</span> {me ? new Date(me.created_at).toLocaleDateString("pt-BR") : "—"}</p>
        </div>
        <button
          onClick={logout}
          className="mt-2 px-4 py-2 border border-red-200 text-red-600 rounded text-sm hover:bg-red-50"
        >
          Sair
        </button>
      </section>

      <section>
        <h2 className="font-semibold text-lg mb-4">Notificações</h2>
        <TelegramConnect />
      </section>
    </div>
  );
}
