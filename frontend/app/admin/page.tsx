"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface CollectorStatus {
  total_active_properties: number;
  last_collection_at: string | null;
  new_today: number;
  alerts_sent_today: number;
}

interface HealthStatus {
  status: string;
  db: string;
}

export default function AdminPage() {
  const { data: status, isLoading: statusLoading } = useQuery<CollectorStatus>({
    queryKey: ["admin", "status"],
    queryFn: () => api.get("/admin/status").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: health } = useQuery<HealthStatus>({
    queryKey: ["admin", "health"],
    queryFn: () => api.get("/admin/health").then((r) => r.data),
    refetchInterval: 30_000,
  });

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Painel Admin</h1>

      <section className="space-y-4">
        <h2 className="font-semibold text-lg">Status do sistema</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatusCard
            label="Imóveis ativos"
            value={statusLoading ? "..." : String(status?.total_active_properties ?? 0)}
            color="blue"
          />
          <StatusCard
            label="Novos hoje"
            value={statusLoading ? "..." : String(status?.new_today ?? 0)}
            color="green"
          />
          <StatusCard
            label="Alertas hoje"
            value={statusLoading ? "..." : String(status?.alerts_sent_today ?? 0)}
            color="yellow"
          />
          <StatusCard
            label="Banco de dados"
            value={health?.db === "connected" ? "Online" : "Erro"}
            color={health?.db === "connected" ? "green" : "red"}
          />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-semibold text-lg">Coletores</h2>
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-gray-600">Banco</th>
                <th className="px-4 py-3 text-left text-gray-600">Última coleta</th>
                <th className="px-4 py-3 text-left text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="px-4 py-3 font-medium">Caixa Econômica Federal</td>
                <td className="px-4 py-3 text-gray-500">
                  {status?.last_collection_at ? formatDate(status.last_collection_at) : "Nunca"}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-700">
                    Ativo
                  </span>
                </td>
              </tr>
              {["Banco do Brasil", "BRB", "Banco do Nordeste"].map((banco) => (
                <tr key={banco} className="border-b last:border-0">
                  <td className="px-4 py-3 text-gray-400">{banco}</td>
                  <td className="px-4 py-3 text-gray-300">—</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-400">
                      Fase 3
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function StatusCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: "blue" | "green" | "yellow" | "red";
}) {
  const colorMap = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    red: "bg-red-50 text-red-700",
  };
  return (
    <div className={`rounded-lg p-4 ${colorMap[color]}`}>
      <p className="text-xs opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}
