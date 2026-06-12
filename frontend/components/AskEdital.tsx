"use client";

import { useState } from "react";
import api from "@/lib/api";

interface Citation {
  chunk_id: string;
  quote: string;
}

interface AskResult {
  answer: string;
  citations: Citation[];
  not_found: boolean;
}

export function AskEdital({ propertyId }: { propertyId: string }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post<AskResult>(`/properties/${propertyId}/ask`, {
        question,
      });
      setResult(data);
    } catch (err: any) {
      if (err?.response?.status === 403) {
        setError("Esta funcionalidade exige o plano Premium.");
      } else if (err?.response?.status === 429) {
        setError("Limite de perguntas do dia atingido.");
      } else {
        setError("Erro ao consultar o edital. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-lg">💬</span>
        <h3 className="font-semibold text-gray-800">Pergunte ao edital</h3>
      </div>

      <form onSubmit={submit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ex: Quem paga dívidas de condomínio?"
          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg disabled:opacity-50 hover:bg-blue-700 transition"
        >
          {loading ? "..." : "Perguntar"}
        </button>
      </form>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
      )}

      {result && result.not_found && (
        <p className="text-sm text-gray-500 italic">
          Esta informação não consta no edital ou matrícula disponíveis.
        </p>
      )}

      {result && !result.not_found && (
        <div className="space-y-3">
          <p className="text-sm text-gray-800 leading-relaxed">{result.answer}</p>

          {result.citations.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Fonte no edital
              </p>
              {result.citations.map((c, i) => (
                <blockquote
                  key={i}
                  className="border-l-4 border-blue-300 pl-3 text-xs text-gray-600 italic"
                >
                  "{c.quote}"
                </blockquote>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
