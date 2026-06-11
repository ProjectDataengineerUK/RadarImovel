import type { RiskScore } from "@/lib/types";

const RISK_STYLES: Record<string, string> = {
  low: "bg-green-100 text-green-800 border-green-200",
  moderate: "bg-yellow-100 text-yellow-800 border-yellow-200",
  elevated: "bg-orange-100 text-orange-800 border-orange-200",
  high: "bg-red-100 text-red-800 border-red-200",
  critical: "bg-gray-900 text-white border-gray-700",
};

const RISK_LABELS: Record<string, string> = {
  low: "Baixo",
  moderate: "Moderado",
  elevated: "Elevado",
  high: "Alto",
  critical: "Crítico",
};

interface Props {
  score: Pick<RiskScore, "score_total" | "risk_level" | "score_partial">;
  size?: "sm" | "md" | "lg";
}

export function RiskScoreBadge({ score, size = "md" }: Props) {
  const style = RISK_STYLES[score.risk_level] ?? RISK_STYLES.moderate;
  const label = RISK_LABELS[score.risk_level] ?? score.risk_level;
  const textSize = size === "sm" ? "text-xs" : size === "lg" ? "text-base" : "text-sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-semibold ${textSize} ${style}`}
    >
      <span>{label}</span>
      <span className="font-bold">{score.score_total}</span>
      {score.score_partial && (
        <span className="text-[10px] opacity-70" title="Score parcial — fontes indisponíveis">
          *
        </span>
      )}
    </span>
  );
}
