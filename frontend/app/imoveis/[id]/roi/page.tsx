"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { ROICalculator } from "@/components/ROICalculator";
import { SecondAuctionBadge } from "@/components/SecondAuctionBadge";
import { MarketComparisonBadge } from "@/components/MarketComparisonBadge";

interface Property {
  id: string;
  external_code: string;
  title: string;
  city: string;
  state: string;
  current_value: number;
  auction_stage?: string | null;
  discount_vs_market_pct?: number | null;
  market_price_per_sqm?: number | null;
}

export default function ROIPage() {
  const { id } = useParams<{ id: string }>();

  const { data: prop, isLoading, error } = useQuery<Property>({
    queryKey: ["property", id],
    queryFn: () => axios.get(`/api/properties/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-500">
        Carregando imóvel...
      </div>
    );
  }

  if (error || !prop) {
    return (
      <div className="flex min-h-screen items-center justify-center text-red-500">
        Imóvel não encontrado.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-1 text-xl font-bold text-gray-900 dark:text-white">{prop.title}</h1>
      <p className="mb-3 text-sm text-gray-500">
        {prop.city}/{prop.state}
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        <SecondAuctionBadge auctionStage={prop.auction_stage} />
        <MarketComparisonBadge
          discountVsMarketPct={prop.discount_vs_market_pct}
          marketPricePerSqm={prop.market_price_per_sqm}
        />
      </div>

      <div className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-sm text-gray-600 dark:text-gray-400">Lance mínimo</p>
        <p className="text-2xl font-bold text-blue-700 dark:text-blue-400">
          R${" "}
          {prop.current_value.toLocaleString("pt-BR", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
          })}
        </p>
      </div>

      <ROICalculator propertyId={prop.external_code || prop.id} lanceValue={prop.current_value} />
    </div>
  );
}
