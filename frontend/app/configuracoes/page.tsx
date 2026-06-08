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
    <div className="min-h-screen bg-gray-950">
      <div className="border-b border-gray-800 px-8 py-5">
        <h1 className="text-lg font-semibold text-white">Configurações</h1>
        <p className="text-xs text-gray-500 mt-0.5">Gerencie sua conta e notificações</p>
      </div>

      <div className="px-8 py-6 max-w-2xl space-y-4">
        {/* Conta */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">Conta</h2>
          </div>
          <div className="px-6 py-5 space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm font-bold text-white shrink-0">
                {firebaseUser?.email?.charAt(0).toUpperCase() ?? "U"}
              </div>
              <div>
                <p className="text-sm font-medium text-white">
                  {firebaseUser?.displayName ?? firebaseUser?.email?.split("@")[0]}
                </p>
                <p className="text-xs text-gray-500">{firebaseUser?.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="bg-gray-800/50 rounded-lg px-4 py-3">
                <p className="text-xs text-gray-500 mb-0.5">Membro desde</p>
                <p className="text-sm text-white font-medium">
                  {me ? new Date(me.created_at).toLocaleDateString("pt-BR", { month: "long", year: "numeric" }) : "—"}
                </p>
              </div>
              <div className="bg-gray-800/50 rounded-lg px-4 py-3">
                <p className="text-xs text-gray-500 mb-0.5">Telegram</p>
                <p className="text-sm font-medium">
                  {me?.telegram_connected
                    ? <span className="text-emerald-400">Conectado</span>
                    : <span className="text-gray-400">Não conectado</span>}
                </p>
              </div>
            </div>

            <div className="pt-1 border-t border-gray-800">
              <button
                onClick={logout}
                className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Sair da conta
              </button>
            </div>
          </div>
        </div>

        {/* Notificações */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">Notificações</h2>
            <p className="text-xs text-gray-500 mt-0.5">Conecte canais para receber alertas de novos imóveis</p>
          </div>
          <div className="px-6 py-5">
            <TelegramConnect />
          </div>
        </div>
      </div>
    </div>
  );
}
