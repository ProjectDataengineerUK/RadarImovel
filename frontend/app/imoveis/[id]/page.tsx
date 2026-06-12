"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useProperty } from "@/hooks/useProperties";
import { formatCurrency, formatDate } from "@/lib/utils";
import ScoreBadge from "@/components/ScoreBadge";
import EditalSection from "@/components/EditalSection";
import { RiskScoreBadge } from "@/components/RiskScoreBadge";
import { RiskRadarChart } from "@/components/RiskRadarChart";
import { RiskIndicatorList } from "@/components/RiskIndicatorList";
import { DueDiligenceButton } from "@/components/DueDiligenceButton";
import { usePropertyRisk } from "@/hooks/useRisk";
import { usePropertyOffers, usePropertyMatricula } from "@/hooks/useProperties";
import { PriceDropForecast } from "@/components/PriceDropForecast";
import { AskEdital } from "@/components/AskEdital";
import { ViabilityCalculator } from "@/components/ViabilityCalculator";
import { MatriculaSection } from "@/components/MatriculaSection";
import { usePlan } from "@/hooks/usePlan";

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, isError } = useProperty(id);
  const { data: riskScore } = usePropertyRisk(id);
  const { data: offersData } = usePropertyOffers(id);
  const { data: matricula } = usePropertyMatricula(id);
  const { hasFeature } = usePlan();

  if (isLoading) return <div className="p-8 text-gray-500">Carregando...</div>;
  if (isError || !data) return <div className="p-8 text-red-500">Imóvel não encontrado.</div>;

  const { property: p, changes, edital_processed, edital } = data;

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

      {offersData && offersData.length > 1 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Disponível em {offersData.length} fontes</h2>
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-600">Fonte</th>
                  <th className="px-4 py-2 text-left text-gray-600">Preço</th>
                  <th className="px-4 py-2 text-left text-gray-600">Modalidade</th>
                  <th className="px-4 py-2 text-left text-gray-600">Data</th>
                  <th className="px-4 py-2 text-left text-gray-600"></th>
                </tr>
              </thead>
              <tbody>
                {offersData.map((o) => (
                  <tr key={o.id} className="border-b last:border-0">
                    <td className="px-4 py-2 font-medium">{o.source_name}</td>
                    <td className="px-4 py-2 text-blue-700 font-semibold">{formatCurrency(o.price)}</td>
                    <td className="px-4 py-2 text-gray-600">{o.modality}</td>
                    <td className="px-4 py-2 text-gray-400">{o.auction_date ? formatDate(o.auction_date) : "—"}</td>
                    <td className="px-4 py-2">
                      <a
                        href={o.official_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-xs"
                      >
                        Ver →
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {edital_processed && edital && <EditalSection edital={edital} />}

      {hasFeature("calculator") && <ViabilityCalculator propertyId={id} />}

      <div className="rounded-xl border p-6">
        <MatriculaSection matricula={matricula ?? null} />
      </div>

      {hasFeature("price_forecast") && <PriceDropForecast propertyId={id} />}

      {edital_processed && hasFeature("ask") && <AskEdital propertyId={id} />}

      {riskScore && (
        <div className="space-y-4 rounded-xl border p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Risco do Imóvel</h2>
            <div className="flex items-center gap-3">
              <RiskScoreBadge score={riskScore} size="lg" />
              {hasFeature("due_diligence_pdf") && <DueDiligenceButton propertyId={id} />}
            </div>
          </div>
          <RiskRadarChart score={riskScore} />
          <RiskIndicatorList indicators={riskScore.indicators} />
        </div>
      )}

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
