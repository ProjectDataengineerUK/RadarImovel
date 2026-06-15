"use client";

interface SecondAuctionBadgeProps {
  auctionStage?: string | null;
  dropPct?: number | null;
}

export function SecondAuctionBadge({ auctionStage, dropPct }: SecondAuctionBadgeProps) {
  if (auctionStage !== "segunda_praca") return null;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full bg-red-600 px-2 py-0.5 text-xs font-bold text-white"
      title="Imóvel em 2ª Praça — lance mínimo reduzido"
    >
      🔥 2ª Praça
      {dropPct != null && ` -${dropPct.toFixed(0)}%`}
    </span>
  );
}
