"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMe, PlanInfo } from "@/lib/entitlements";

interface UsePlanResult {
  plan: PlanInfo | undefined;
  role: string | undefined;
  isLoading: boolean;
  hasFeature: (flag: string) => boolean;
}

export function usePlan(): UsePlanResult {
  const { data, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    staleTime: 60_000,
  });

  return {
    plan: data?.plan,
    role: data?.role,
    isLoading,
    hasFeature: (flag: string) => data?.plan?.features?.[flag] ?? false,
  };
}
