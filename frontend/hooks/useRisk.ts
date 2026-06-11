"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { RiskHeatmap, RiskScore } from "@/lib/types";

export function usePropertyRisk(propertyId: string) {
  return useQuery<RiskScore>({
    queryKey: ["risk", propertyId],
    queryFn: () => api.get(`/properties/${propertyId}/risk`).then((r) => r.data),
    enabled: !!propertyId,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useRiskHeatmap(uf?: string) {
  return useQuery<RiskHeatmap>({
    queryKey: ["risk-heatmap", uf],
    queryFn: () =>
      api.get("/map/risk-heatmap", { params: uf ? { uf } : {} }).then((r) => r.data),
    staleTime: 10 * 60_000,
  });
}
