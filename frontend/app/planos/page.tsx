"use client";

import { Suspense, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import api from "@/lib/api";

interface Plan {
  id: string;
  code: string;
  name: string;
  description: string | null;
  price_brl: number;
  discount_brl: number;
  stripe_price_id_monthly: string | null;
  stripe_price_id_annual: string | null;
  sort_order: number;
  features: Record<string, boolean>;
  limits: Record<string, number>;
}

interface PlansResponse {
  plans: Plan[];
  features: { key: string; description: string }[];
  quotas: { key: string; period: string; description: string }[];
}

function fmt(cents: number) {
  return (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const FEATURE_ICONS: Record<string, string> = {
  risk_score: "🛡️",
  due_diligence_pdf: "📄",
  export: "📊",
  calculator: "🧮",
  portfolio: "📁",
  realtime_alerts: "⚡",
  whatsapp_channel: "💬",
  ask: "🤖",
  price_forecast: "📈",
  api_access: "🔌",
};

function PlanosContent() {
  const searchParams = useSearchParams();
  const checkoutStatus = searchParams.get("checkout");
  const [billing, setBilling] = useState<"monthly" | "annual">("monthly");

  const { data: plansData, isLoading } = useQuery<PlansResponse>({
    queryKey: ["plans-public"],
    queryFn: () => api.get("/plans").then((r) => r.data),
  });

  const plans = plansData?.plans ?? [];
  const catalog = plansData ? { features: plansData.features, quotas: plansData.quotas } : undefined;

  const checkoutMutation = useMutation({
    mutationFn: ({ plan_code }: { plan_code: string }) =>
      api.post("/billing/checkout", { plan_code, billing }).then((r) => r.data),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
  });

  const portalMutation = useMutation({
    mutationFn: () => api.post("/billing/portal").then((r) => r.data),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
  });

  const activePlans = plans.filter((p) => p.code !== "free").sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Checkout feedback */}
      {checkoutStatus === "success" && (
        <div className="bg-emerald-500/10 border-b border-emerald-500/20 px-8 py-3 text-sm text-emerald-400 text-center">
          ✓ Assinatura ativada com sucesso! Bem-vindo ao Radar Imóvel Premium.
        </div>
      )}
      {checkoutStatus === "cancelled" && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-8 py-3 text-sm text-amber-400 text-center">
          Checkout cancelado. Você pode assinar a qualquer momento.
        </div>
      )}

      <div className="max-w-5xl mx-auto px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-white">Escolha seu plano</h1>
          <p className="text-gray-400 mt-2">Acesse inteligência de mercado para leilões e imóveis bancários</p>

          {/* Toggle mensal/anual */}
          <div className="inline-flex items-center mt-6 bg-gray-900 rounded-lg p-1 border border-gray-800">
            <button
              onClick={() => setBilling("monthly")}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                billing === "monthly" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              Mensal
            </button>
            <button
              onClick={() => setBilling("annual")}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                billing === "annual" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              Anual
              {activePlans.some((p) => p.discount_brl > 0) && (
                <span className="ml-1.5 text-xs bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded">
                  economize
                </span>
              )}
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {activePlans.map((plan) => {
              const monthlyPrice = plan.price_brl;
              const annualMonthly = plan.discount_brl > 0
                ? Math.round((plan.price_brl * 12 - plan.discount_brl) / 12)
                : plan.price_brl;
              const displayPrice = billing === "annual" ? annualMonthly : monthlyPrice;
              const savingsAnnual = plan.discount_brl;
              const isPremium = plan.code === "premium";
              const hasStripe = billing === "monthly"
                ? !!plan.stripe_price_id_monthly
                : !!plan.stripe_price_id_annual;

              return (
                <div
                  key={plan.id}
                  className={`relative bg-gray-900 border rounded-2xl p-6 flex flex-col gap-5 ${
                    isPremium
                      ? "border-blue-500/50 shadow-lg shadow-blue-500/10"
                      : "border-gray-800"
                  }`}
                >
                  {isPremium && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                        Mais popular
                      </span>
                    </div>
                  )}

                  <div>
                    <h2 className="text-white font-bold text-lg">{plan.name}</h2>
                    {plan.description && (
                      <p className="text-gray-400 text-sm mt-1">{plan.description}</p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-end gap-1">
                      <span className="text-3xl font-bold text-white">{fmt(displayPrice)}</span>
                      <span className="text-gray-500 text-sm mb-1">/mês</span>
                    </div>
                    {billing === "annual" && savingsAnnual > 0 && (
                      <p className="text-emerald-400 text-xs mt-0.5">
                        Economia de {fmt(savingsAnnual)}/ano vs. mensal
                      </p>
                    )}
                  </div>

                  <ul className="space-y-2 flex-1">
                    {catalog?.features.map((f) => (
                      <li key={f.key} className="flex items-start gap-2 text-sm">
                        <span className={plan.features[f.key] ? "text-emerald-400 mt-0.5" : "text-gray-700 mt-0.5"}>
                          {plan.features[f.key] ? "✓" : "✗"}
                        </span>
                        <span className={plan.features[f.key] ? "text-gray-300" : "text-gray-600"}>
                          {FEATURE_ICONS[f.key]} {f.description}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <div className="border-t border-gray-800 pt-4 space-y-1.5">
                    {catalog?.quotas.map((q) => (
                      <div key={q.key} className="flex justify-between text-xs text-gray-500">
                        <span>{q.description}</span>
                        <span className="text-gray-300 font-mono">{plan.limits[q.key] ?? "—"}</span>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => checkoutMutation.mutate({ plan_code: plan.code })}
                    disabled={!hasStripe || checkoutMutation.isPending}
                    className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                      isPremium
                        ? "bg-blue-600 hover:bg-blue-500 text-white"
                        : "bg-gray-800 hover:bg-gray-700 text-white"
                    }`}
                  >
                    {checkoutMutation.isPending ? "Redirecionando..." : !hasStripe ? "Em breve" : "Assinar agora"}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className="text-center mt-10">
          <button
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            Gerenciar assinatura existente →
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PlanosPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-950 flex items-center justify-center"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>}>
      <PlanosContent />
    </Suspense>
  );
}
