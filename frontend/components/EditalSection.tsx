import type { Edital } from "@/lib/types";
import { cn, formatCurrency, formatDate } from "@/lib/utils";

interface EditalSectionProps {
  edital: Edital;
}

const OCCUPANCY_LABELS: Record<string, string> = {
  livre: "Livre / desocupado",
  locado: "Locado",
  ocupado_sem_acao: "Ocupado (sem ação judicial)",
  ocupado_com_acao_judicial: "Ocupado (com ação judicial)",
  unknown: "Não informado",
};

const PAYMENT_LABELS: Record<string, string> = {
  vista: "À vista",
  financiamento_caixa: "Financiamento Caixa",
  fgts: "FGTS",
  carta_credito: "Carta de crédito",
  consorcio: "Consórcio",
};

const ENCUMBRANCE_LABELS: Record<string, string> = {
  iptu: "IPTU",
  condominio: "Condomínio",
  hipoteca: "Hipoteca",
  outros: "Outros",
};

function riskStyle(level: string | null): string {
  if (level === "low") return "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/25";
  if (level === "high") return "bg-red-500/15 text-red-400 ring-1 ring-red-500/25";
  return "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/25";
}

function riskLabel(level: string | null): string {
  if (level === "low") return "Baixo";
  if (level === "high") return "Alto";
  if (level === "medium") return "Médio";
  return "—";
}

export default function EditalSection({ edital }: EditalSectionProps) {
  const modalities = edital.payment_modalities ?? [];
  const flags = edital.risk_flags ?? [];
  const encumbrances = edital.encumbrances ?? [];

  return (
    <section className="rounded-lg border border-gray-700 bg-gray-800/50 p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">Edital (extraído por IA)</h2>
        <span
          className={cn(
            "inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold",
            riskStyle(edital.risk_level),
          )}
        >
          Risco {riskLabel(edital.risk_level)}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <EditalField
          label="1ª praça"
          value={edital.auction_date_1st ? formatDate(edital.auction_date_1st) : "—"}
        />
        <EditalField
          label="2ª praça"
          value={edital.auction_date_2nd ? formatDate(edital.auction_date_2nd) : "—"}
        />
        <EditalField
          label="Lance mínimo (1ª)"
          value={edital.minimum_bid_1st !== null ? formatCurrency(edital.minimum_bid_1st) : "—"}
        />
        <EditalField
          label="Avaliação oficial"
          value={edital.appraisal_value !== null ? formatCurrency(edital.appraisal_value) : "—"}
        />
        <EditalField
          label="Ocupação"
          value={OCCUPANCY_LABELS[edital.occupancy_detail ?? "unknown"] ?? "—"}
        />
        <EditalField
          label="Dívidas estimadas"
          value={
            edital.total_debt_estimate !== null
              ? formatCurrency(edital.total_debt_estimate)
              : "—"
          }
          danger={!!edital.total_debt_estimate && edital.total_debt_estimate > 0}
        />
        <EditalField label="Leiloeiro" value={edital.auctioneer_name ?? "—"} />
        <EditalField label="Matrícula" value={edital.registration_number ?? "—"} />
        <EditalField label="Nº edital" value={edital.edital_number ?? "—"} />
      </div>

      {modalities.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 mb-2">Formas de pagamento</p>
          <div className="flex flex-wrap gap-2">
            {modalities.map((m) => (
              <span
                key={m}
                className="px-2 py-0.5 rounded-md text-xs bg-blue-500/15 text-blue-300 ring-1 ring-blue-500/25"
              >
                {PAYMENT_LABELS[m] ?? m}
              </span>
            ))}
          </div>
        </div>
      )}

      {encumbrances.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 mb-2">Ônus e dívidas herdáveis</p>
          <div className="rounded-md border border-gray-700 overflow-hidden">
            <table className="w-full text-sm">
              <tbody>
                {encumbrances.map((e, i) => (
                  <tr key={i} className="border-b border-gray-700 last:border-0">
                    <td className="px-3 py-2 text-gray-300">
                      {ENCUMBRANCE_LABELS[e.type] ?? e.type}
                    </td>
                    <td className="px-3 py-2 text-gray-400">{e.description || "—"}</td>
                    <td className="px-3 py-2 text-right text-amber-400 tabular-nums">
                      {e.amount_approx !== null ? formatCurrency(e.amount_approx) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {flags.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 mb-2">Sinais de risco</p>
          <div className="flex flex-wrap gap-2">
            {flags.map((f) => (
              <span
                key={f}
                className="px-2 py-0.5 rounded-md text-xs bg-red-500/15 text-red-300 ring-1 ring-red-500/25"
              >
                {f.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {edital.extraction_confidence !== null && (
        <p className="text-xs text-gray-500">
          Confiança da extração: {Math.round((edital.extraction_confidence ?? 0) * 100)}%
          {edital.processed_at ? ` · processado em ${formatDate(edital.processed_at)}` : ""}
        </p>
      )}
    </section>
  );
}

function EditalField({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className={cn("mt-1 font-medium", danger ? "text-red-400" : "text-gray-200")}>{value}</p>
    </div>
  );
}
