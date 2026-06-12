import api from "@/lib/api";

export interface PlanInfo {
  code: string;
  features: Record<string, boolean>;
  limits: Record<string, number>;
}

export interface MeResponse {
  id: string;
  firebase_uid: string;
  role: string;
  telegram_connected: boolean;
  created_at: string;
  plan: PlanInfo;
}

export async function fetchMe(): Promise<MeResponse> {
  const res = await api.get<MeResponse>("/users/me");
  return res.data;
}

export const FEATURE_LABELS: Record<string, string> = {
  risk_score: "Score de risco multidimensional",
  due_diligence_pdf: "Relatório PDF de due diligence",
  export: "Export CSV/Excel",
  calculator: "Calculadora de viabilidade",
  portfolio: "Carteira Kanban",
  realtime_alerts: "Alertas em tempo real (<15min)",
  whatsapp_channel: "Alertas por WhatsApp",
  ask: "Pergunte ao edital",
  price_forecast: "Curva de desconto preditiva",
  api_access: "API B2B",
};

export const PLAN_DISPLAY: Record<string, { label: string; color: string }> = {
  free: { label: "Free", color: "text-gray-400" },
  pro: { label: "Pro", color: "text-blue-400" },
  premium: { label: "Premium", color: "text-amber-400" },
};
