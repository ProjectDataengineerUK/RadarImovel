"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";

interface ViabilityScenario {
  scenario: "venda" | "aluguel";
  total_investment: number;
  net_profit: number;
  roi_pct: number;
  payback_months: number | null;
  monthly_rent: number;
  annual_net_yield_pct: number;
  irr_annual_pct: number | null;
  npv: number;
  viable: boolean;
  warnings: string[];
  acquisition_costs: number;
  renovation_cost: number;
  sale_price_estimate: number;
  discount_vs_appraisal_pct: number;
}

interface ViabilityResponse {
  property_id: string;
  scenarios: ViabilityScenario[];
}

interface Props {
  propertyId: string;
}

const R$ = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const pct = (v: number) => `${v.toFixed(2)}%`;

export function ViabilityCalculator({ propertyId }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    monthly_condo: "",
    area_m2: "",
    existing_debt: "",
    hold_years: "5",
  });

  const { mutate, data, isPending, isError } = useMutation<ViabilityResponse>({
    mutationFn: () =>
      api.post(`/properties/${propertyId}/viability`, {
        monthly_condo: form.monthly_condo ? Number(form.monthly_condo) : null,
        area_m2: form.area_m2 ? Number(form.area_m2) : null,
        existing_debt: Number(form.existing_debt) || 0,
        hold_years: Number(form.hold_years) || 5,
      }).then((r) => r.data),
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full mt-4 border border-blue-600 text-blue-600 rounded-lg px-4 py-2 text-sm hover:bg-blue-50 transition"
      >
        Calculadora de Viabilidade
      </button>
    );
  }

  return (
    <div className="mt-4 border rounded-lg p-4 bg-gray-50">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-gray-700">Calculadora de Viabilidade</h3>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        {[
          { key: "monthly_condo", label: "Condomínio/mês (R$)", placeholder: "600" },
          { key: "area_m2", label: "Área (m²)", placeholder: "ex: 80" },
          { key: "existing_debt", label: "Dívidas herdadas (R$)", placeholder: "0" },
          { key: "hold_years", label: "Horizonte (anos)", placeholder: "5" },
        ].map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="text-xs text-gray-500 block mb-1">{label}</label>
            <input
              type="number"
              value={form[key as keyof typeof form]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              className="w-full border rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
        ))}
      </div>

      <button
        onClick={() => mutate()}
        disabled={isPending}
        className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-60 transition"
      >
        {isPending ? "Calculando…" : "Calcular"}
      </button>

      {isError && <p className="text-red-500 text-xs mt-2">Erro ao calcular. Verifique sua assinatura.</p>}

      {data && (
        <div className="mt-4 space-y-4">
          {data.scenarios.map((s) => (
            <div key={s.scenario} className={`rounded-lg border p-3 ${s.viable ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold text-sm capitalize">{s.scenario === "venda" ? "🏷️ Venda Rápida" : "🏠 Aluguel + Saída"}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${s.viable ? "bg-green-200 text-green-800" : "bg-red-200 text-red-800"}`}>
                  {s.viable ? "Viável" : "Inviável"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-700">
                <span className="text-gray-500">Investimento total</span>
                <span className="font-medium">{R$(s.total_investment)}</span>
                <span className="text-gray-500">Custos de aquisição</span>
                <span>{R$(s.acquisition_costs)}</span>
                <span className="text-gray-500">Reforma estimada</span>
                <span>{R$(s.renovation_cost)}</span>

                {s.scenario === "venda" ? (
                  <>
                    <span className="text-gray-500">Preço de venda est.</span>
                    <span>{R$(s.sale_price_estimate)}</span>
                    <span className="text-gray-500">Lucro líquido</span>
                    <span className={s.net_profit >= 0 ? "text-green-700 font-semibold" : "text-red-600 font-semibold"}>{R$(s.net_profit)}</span>
                    <span className="text-gray-500">ROI</span>
                    <span className="font-semibold">{pct(s.roi_pct)}</span>
                    {s.payback_months && <><span className="text-gray-500">Payback</span><span>{s.payback_months} meses</span></>}
                  </>
                ) : (
                  <>
                    <span className="text-gray-500">Aluguel/mês</span>
                    <span>{R$(s.monthly_rent)}</span>
                    <span className="text-gray-500">Yield líquido a.a.</span>
                    <span className="font-semibold">{pct(s.annual_net_yield_pct)}</span>
                    {s.irr_annual_pct !== null && <><span className="text-gray-500">TIR anual</span><span className="font-semibold">{pct(s.irr_annual_pct)}</span></>}
                    <span className="text-gray-500">VPL</span>
                    <span className={s.npv >= 0 ? "text-green-700 font-semibold" : "text-red-600 font-semibold"}>{R$(s.npv)}</span>
                  </>
                )}
                <span className="text-gray-500">Desconto vs. avaliação</span>
                <span>{pct(s.discount_vs_appraisal_pct)}</span>
              </div>

              {s.warnings.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {s.warnings.map((w) => (
                    <span key={w} className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded-full">⚠ {w}</span>
                  ))}
                </div>
              )}
            </div>
          ))}

          <p className="text-xs text-gray-400">* Estimativas baseadas em médias de mercado. Consulte um corretor para valores precisos.</p>
        </div>
      )}
    </div>
  );
}
