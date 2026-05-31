"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useProperty } from "@/hooks/useProperties";
import { formatCurrency, formatDate } from "@/lib/utils";
import ScoreBadge from "@/components/ScoreBadge";

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useProperty(id);

  if (isLoading) return <div className="p-8 text-gray-500">Carregando...</div>;
  if (isError || !data) return <div className="p-8 text-red-500">Imóvel não encontrado.</div>;

  const { property: p, changes } = data;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/imoveis" className="text-sm text-blue-600 hover:underline">← Voltar</Link>
          <h1 className="text-2xl font-bold mt-2">{p.title ?? `${p.property_type} em ${p.city}/${p.state}`}</h1>
          <p className="text-gray-500 text-sm mt-1">{p.address}{p.neighborhood ? `, ${p.neighborhood}` : ""} · {p.city}/{p.state}</p>
        </div>
        <ScoreBadge score={p.opportunity_score} className="text-base px-3 py-1" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCard label="Preço atual" value={formatCurrency(p.current_value)} highlight />
        <InfoCard label="Desconto" value={p.discount_percent ? `${p.discount_percent}%` : "—"} />
        <InfoCard label="Avaliação" value={p.appraisal_value ? formatCurrency(p.appraisal_value) : "—"} />
        <InfoCard label="Modalidade" value={p.sale_modality} />
        <InfoCard label="Situação" value={p.occupancy_status} />
        <InfoCard label="Tipo" value={p.property_type} />
        {p.area_total && <InfoCard label="Área total" value={`${p.area_total} m²`} />}
        {p.bedrooms !== null && <InfoCard label="Quartos" value={String(p.bedrooms)} />}
        {p.auction_date && <InfoCard label="Data do leilão" value={formatDate(p.auction_date)} />}
        <InfoCard label="Cadastrado em" value={formatDate(p.first_seen_at)} />
      </div>

      <div className="flex gap-3">
        <a
          href={p.official_url}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
        >
          Ver no site oficial
        </a>
      </div>

      {changes.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Histórico de mudanças</h2>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-600">Campo</th>
                  <th className="px-4 py-2 text-left text-gray-600">Antes</th>
                  <th className="px-4 py-2 text-left text-gray-600">Depois</th>
                  <th className="px-4 py-2 text-left text-gray-600">Detectado em</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((c) => (
                  <tr key={c.id} className="border-b last:border-0">
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">{c.field_name}</td>
                    <td className="px-4 py-2 text-red-500">{c.old_value ?? "—"}</td>
                    <td className="px-4 py-2 text-green-600">{c.new_value ?? "—"}</td>
                    <td className="px-4 py-2 text-gray-400">{formatDate(c.detected_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoCard({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-1 font-semibold ${highlight ? "text-xl text-blue-700" : "text-gray-800"}`}>{value}</p>
    </div>
  );
}
