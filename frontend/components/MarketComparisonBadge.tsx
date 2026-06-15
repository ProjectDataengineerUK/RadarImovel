"use client";

interface MarketComparisonBadgeProps {
  discountVsMarketPct?: number | null;
  marketPricePerSqm?: number | null;
}

export function MarketComparisonBadge({
  discountVsMarketPct,
  marketPricePerSqm,
}: MarketComparisonBadgeProps) {
  if (discountVsMarketPct == null) return null;

  const isGood = discountVsMarketPct >= 20;
  const color = isGood ? "bg-green-600" : discountVsMarketPct >= 0 ? "bg-yellow-500" : "bg-gray-500";
  const label =
    discountVsMarketPct >= 0
      ? `-${discountVsMarketPct.toFixed(0)}% vs mercado`
      : `+${Math.abs(discountVsMarketPct).toFixed(0)}% acima mercado`;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold text-white ${color}`}
      title={
        marketPricePerSqm
          ? `Preço médio de mercado: R$ ${marketPricePerSqm.toLocaleString("pt-BR")}/m²`
          : "Comparação com mercado FipeZap"
      }
    >
      📊 {label}
    </span>
  );
}
