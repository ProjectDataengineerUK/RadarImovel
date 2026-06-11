"use client";

import { useState } from "react";
import api from "@/lib/api";

interface Props {
  propertyId: string;
}

export function DueDiligenceButton({ propertyId }: Props) {
  const [loading, setLoading] = useState(false);

  async function handleDownload() {
    setLoading(true);
    try {
      const resp = await api.get(`/properties/${propertyId}/risk/report`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `due_diligence_${propertyId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Relatório não disponível. O score de risco ainda não foi calculado.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50"
    >
      {loading ? "Gerando PDF…" : "Exportar Due Diligence PDF"}
    </button>
  );
}
