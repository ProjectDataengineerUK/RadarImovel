"use client";

import { useState } from "react";
import axios from "axios";

interface ROIResult {
  roi_pct: number;
  yield_annual_pct: number | null;
  payback_months: number | null;
  cdi_equivalent_pct: number;
  net_gain_vs_cdi_pct: number;
  assumptions: Record<string, unknown>;
}

interface ROICalculatorProps {
  propertyId: string;
  lanceValue: number;
}

const INTENTIONS = [
  { value: "revenda", label: "Revenda" },
  { value: "aluguel", label: "Aluguel" },
  { value: "moradia", label: "Moradia" },
];

export function ROICalculator({ propertyId, lanceValue }: ROICalculatorProps) {
  const [intention, setIntention] = useState("revenda");
  const [horizon, setHorizon] = useState(60);
  const [areaSqm, setAreaSqm] = useState<number | "">("");
  const [reformCost, setReformCost] = useState(500);
  const [result, setResult] = useState<ROIResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCalc = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await axios.post(`/api/market/properties/${propertyId}/roi`, {
        intention,
        horizon_months: horizon,
        area_sqm: areaSqm || null,
        reform_cost_per_sqm: reformCost,
      });
      setResult(resp.data);
    } catch (e: unknown) {
      setError("Erro ao calcular ROI. Verifique os dados.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <h3 className="mb-3 text-base font-semibold text-gray-800 dark:text-white">
        Calculadora de ROI
      </h3>

      <div className="mb-3 grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">Intenção</label>
          <select
            value={intention}
            onChange={(e) => setIntention(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          >
            {INTENTIONS.map((i) => (
              <option key={i.value} value={i.value}>{i.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            Horizonte (meses)
          </label>
          <input
            type="number"
            value={horizon}
            min={6}
            max={240}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">Área (m²)</label>
          <input
            type="number"
            value={areaSqm}
            placeholder="Ex: 80"
            onChange={(e) => setAreaSqm(e.target.value ? Number(e.target.value) : "")}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            Reforma (R$/m²)
          </label>
          <input
            type="number"
            value={reformCost}
            onChange={(e) => setReformCost(Number(e.target.value))}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
        </div>
      </div>

      <button
        onClick={handleCalc}
        disabled={loading}
        className="w-full rounded bg-blue-600 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Calculando..." : "Calcular ROI"}
      </button>

      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}

      {result && (
        <div className="mt-4 space-y-2">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">ROI Total</span>
            <span className={`font-bold ${result.roi_pct >= 0 ? "text-green-600" : "text-red-600"}`}>
              {result.roi_pct.toFixed(1)}%
            </span>
          </div>
          {result.yield_annual_pct != null && (
            <div className="flex justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Yield Anual</span>
              <span className="font-semibold text-blue-600">{result.yield_annual_pct.toFixed(1)}%</span>
            </div>
          )}
          {result.payback_months != null && (
            <div className="flex justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Payback</span>
              <span className="text-sm">{result.payback_months.toFixed(0)} meses</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">vs CDI</span>
            <span
              className={`font-semibold ${result.net_gain_vs_cdi_pct >= 0 ? "text-green-600" : "text-red-500"}`}
            >
              {result.net_gain_vs_cdi_pct >= 0 ? "+" : ""}
              {result.net_gain_vs_cdi_pct.toFixed(1)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
