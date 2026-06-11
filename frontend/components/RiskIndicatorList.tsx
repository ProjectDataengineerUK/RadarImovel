import type { RiskIndicator } from "@/lib/types";

interface Props {
  indicators: Record<string, RiskIndicator>;
}

export function RiskIndicatorList({ indicators }: Props) {
  const entries = Object.values(indicators);
  if (entries.length === 0) {
    return <p className="text-sm text-gray-500">Nenhum indicador disponível.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-gray-500">
            <th className="pb-2 pr-4 font-medium">Código</th>
            <th className="pb-2 pr-4 font-medium">Valor</th>
            <th className="pb-2 pr-4 font-medium">Fonte</th>
            <th className="pb-2 pr-4 font-medium">Data</th>
            <th className="pb-2 font-medium">Nota</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((ind) => (
            <tr key={ind.code} className="border-b last:border-0">
              <td className="py-2 pr-4 font-mono font-bold">{ind.code}</td>
              <td className="py-2 pr-4">{String(ind.value)}</td>
              <td className="py-2 pr-4 text-xs text-gray-600">{ind.source}</td>
              <td className="py-2 pr-4 text-xs tabular-nums">{ind.date_fetched}</td>
              <td className="py-2 text-xs text-gray-500">{ind.note ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
