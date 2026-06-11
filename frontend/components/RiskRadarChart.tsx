"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { RiskScore } from "@/lib/types";

const DIMENSIONS = [
  { key: "score_juridico", label: "Jurídico" },
  { key: "score_fundiario", label: "Fundiário" },
  { key: "score_fiscal", label: "Fiscal" },
  { key: "score_ocupacao", label: "Ocupação" },
  { key: "score_socioeconomico", label: "Socioecon." },
  { key: "score_mercado", label: "Mercado" },
] as const;

interface Props {
  score: RiskScore;
}

export function RiskRadarChart({ score }: Props) {
  const data = DIMENSIONS.map(({ key, label }) => ({
    subject: label,
    value: score[key],
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
        <Radar
          name="Risco"
          dataKey="value"
          stroke="#ef4444"
          fill="#ef4444"
          fillOpacity={0.3}
        />
        <Tooltip formatter={(v: number) => [`${v.toFixed(1)}`, "Risco"]} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
