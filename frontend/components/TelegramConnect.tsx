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
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-center gap-2">
          <span className="text-green-600 font-semibold">Telegram conectado</span>
          <span className="text-green-500 text-sm">Você receberá alertas via Telegram.</span>
        </div>
        <button
          onClick={() => api.delete("/users/telegram").then(() => qc.invalidateQueries({ queryKey: ["me"] }))}
          className="mt-3 text-xs text-red-500 hover:underline"
        >
          Desconectar
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-6 space-y-4">
      <div>
        <h3 className="font-semibold text-lg">Conectar Telegram</h3>
        <p className="text-sm text-gray-500 mt-1">
          Receba alertas de novos imóveis diretamente no Telegram.
        </p>
      </div>

      {!token ? (
        <button
          onClick={() => generateToken.mutate()}
          disabled={generateToken.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {generateToken.isPending ? "Gerando token..." : "Gerar código de conexão"}
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700">Envie este comando para o bot <strong>@RadarImovelBot</strong>:</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-gray-100 rounded px-3 py-2 text-sm font-mono">/start {token}</code>
            <button
              onClick={copyCommand}
              className="px-3 py-2 border rounded text-sm hover:bg-gray-50"
            >
              {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
          <p className="text-xs text-gray-400">Token expira em 15 minutos.</p>
          <button
            onClick={() => { setToken(null); qc.invalidateQueries({ queryKey: ["me"] }); }}
            className="text-xs text-blue-600 hover:underline"
          >
            Verificar status
          </button>
        </div>
      )}
    </div>
  );
}
