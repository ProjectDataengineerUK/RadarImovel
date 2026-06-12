"use client";

import { usePlan } from "@/hooks/usePlan";

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function FeatureGate({ feature, children, fallback }: FeatureGateProps) {
  const { plan, isLoading } = usePlan();

  if (isLoading) return null;

  if (!plan?.features?.[feature]) {
    if (fallback) return <>{fallback}</>;
    return (
      <div className="rounded-lg border border-dashed border-gray-700 p-6 text-center">
        <p className="text-sm text-gray-500 mb-2">Disponível no plano superior</p>
        <a
          href="/configuracoes/plano"
          className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
        >
          Fazer upgrade →
        </a>
      </div>
    );
  }

  return <>{children}</>;
}
