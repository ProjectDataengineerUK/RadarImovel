"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { User } from "@/lib/types";

export default function TelegramConnect() {
  const qc = useQueryClient();
  const [token, setToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: user } = useQuery<User>({
    queryKey: ["me"],
    queryFn: () => api.get("/users/me").then((r) => r.data),
  });

  const generateToken = useMutation({
    mutationFn: () => api.post<{ token: string; expires_in: number }>("/users/telegram/token").then((r) => r.data),
    onSuccess: (data) => setToken(data.token),
  });

  async function copyCommand() {
    if (!token) return;
    await navigator.clipboard.writeText(`/start ${token}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (user?.telegram_connected) {
    return (
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
            <svg className="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.17 13.59l-2.965-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.983.969z"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-white">Telegram conectado</p>
            <p className="text-xs text-gray-500 mt-0.5">Você receberá alertas de novos imóveis</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          Ativo
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-gray-400" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.17 13.59l-2.965-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.983.969z"/>
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-white">Telegram</p>
          <p className="text-xs text-gray-500">Receba alertas em tempo real no Telegram</p>
        </div>
      </div>

      {!token ? (
        <button
          onClick={() => generateToken.mutate()}
          disabled={generateToken.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {generateToken.isPending ? (
            <>
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Gerando...
            </>
          ) : "Gerar código de conexão"}
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-gray-400">
            Envie este comando para <span className="text-blue-400 font-medium">@RadarImovelBot</span> no Telegram:
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm font-mono text-gray-200 truncate">
              /start {token}
            </code>
            <button
              onClick={copyCommand}
              className="px-3 py-2.5 border border-gray-700 hover:border-gray-600 text-gray-400 hover:text-white rounded-lg text-xs transition-colors shrink-0"
            >
              {copied ? "Copiado ✓" : "Copiar"}
            </button>
          </div>
          <p className="text-xs text-gray-600">Token expira em 15 minutos.</p>
          <button
            onClick={() => { setToken(null); qc.invalidateQueries({ queryKey: ["me"] }); }}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            Verificar status da conexão →
          </button>
        </div>
      )}
    </div>
  );
}
