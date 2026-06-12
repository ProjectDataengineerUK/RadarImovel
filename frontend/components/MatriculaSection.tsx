"use client";

interface Onus {
  type: string;
  credor: string | null;
  valor_approx: number | null;
  averbacao: string | null;
}

interface Proprietario {
  nome: string;
  fracao_pct: number | null;
}

export interface MatriculaData {
  numero_matricula: string | null;
  cartorio: string | null;
  area_total_m2: number | null;
  area_construida_m2: number | null;
  descricao_resumida: string | null;
  proprietarios: Proprietario[];
  onus_reais: Onus[];
  situacao_dominial: string | null;
  data_ultima_averbacao: string | null;
  extraction_confidence: number | null;
  model_used: string | null;
  processed_at: string | null;
}

interface Props {
  matricula: MatriculaData | null;
}

const R$ = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const ONUS_LABEL: Record<string, string> = {
  hipoteca: "Hipoteca",
  penhora: "Penhora",
  alienacao_fiduciaria: "Alienação Fiduciária",
  usufruto: "Usufruto",
  servidao: "Servidão",
  outros: "Outros",
};

export function MatriculaSection({ matricula }: Props) {
  if (!matricula) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 p-4 text-center text-sm text-gray-400">
        Matrícula não disponível. O documento ainda não foi processado.
      </div>
    );
  }

  const confidence = matricula.extraction_confidence ?? 0;
  const confidenceColor = confidence >= 0.8 ? "text-green-600" : confidence >= 0.5 ? "text-yellow-600" : "text-red-500";

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold text-gray-700">Matrícula do Imóvel</h3>
        <span className={`text-xs ${confidenceColor}`}>
          Confiança: {(confidence * 100).toFixed(0)}%
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        {matricula.numero_matricula && (
          <div>
            <span className="text-gray-500 text-xs block">Número da Matrícula</span>
            <span className="font-medium">{matricula.numero_matricula}</span>
          </div>
        )}
        {matricula.cartorio && (
          <div>
            <span className="text-gray-500 text-xs block">Cartório</span>
            <span className="font-medium">{matricula.cartorio}</span>
          </div>
        )}
        {matricula.area_total_m2 !== null && (
          <div>
            <span className="text-gray-500 text-xs block">Área Total</span>
            <span className="font-medium">{matricula.area_total_m2} m²</span>
          </div>
        )}
        {matricula.area_construida_m2 !== null && (
          <div>
            <span className="text-gray-500 text-xs block">Área Construída</span>
            <span className="font-medium">{matricula.area_construida_m2} m²</span>
          </div>
        )}
        {matricula.situacao_dominial && (
          <div>
            <span className="text-gray-500 text-xs block">Situação Dominial</span>
            <span className="font-medium capitalize">{matricula.situacao_dominial.replace(/_/g, " ")}</span>
          </div>
        )}
        {matricula.data_ultima_averbacao && (
          <div>
            <span className="text-gray-500 text-xs block">Última Averbação</span>
            <span className="font-medium">{matricula.data_ultima_averbacao}</span>
          </div>
        )}
      </div>

      {matricula.descricao_resumida && (
        <div>
          <span className="text-gray-500 text-xs block mb-1">Descrição</span>
          <p className="text-sm text-gray-700 bg-gray-50 rounded p-2">{matricula.descricao_resumida}</p>
        </div>
      )}

      {matricula.proprietarios.length > 0 && (
        <div>
          <span className="text-gray-500 text-xs block mb-1 font-medium">Proprietários</span>
          <ul className="space-y-1">
            {matricula.proprietarios.map((p, i) => (
              <li key={i} className="flex justify-between text-sm">
                <span className="text-gray-700">{p.nome}</span>
                {p.fracao_pct !== null && (
                  <span className="text-gray-500 text-xs">{p.fracao_pct.toFixed(1)}%</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {matricula.onus_reais.length > 0 ? (
        <div>
          <span className="text-red-600 text-xs font-semibold block mb-1">⚠ Ônus Reais Ativos</span>
          <ul className="space-y-2">
            {matricula.onus_reais.map((o, i) => (
              <li key={i} className="bg-red-50 border border-red-200 rounded p-2 text-xs">
                <div className="flex justify-between">
                  <span className="font-semibold text-red-700">{ONUS_LABEL[o.type] ?? o.type}</span>
                  {o.valor_approx !== null && <span>{R$(o.valor_approx)}</span>}
                </div>
                {o.credor && <p className="text-gray-600">Credor: {o.credor}</p>}
                {o.averbacao && <p className="text-gray-500">Av. {o.averbacao}</p>}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded p-2 text-xs text-green-700">
          ✓ Sem ônus reais registrados
        </div>
      )}

      <p className="text-xs text-gray-400">
        Extraído via IA ({matricula.model_used ?? "Gemini"}) em{" "}
        {matricula.processed_at ? new Date(matricula.processed_at).toLocaleDateString("pt-BR") : "—"}.
        Verifique sempre a certidão original.
      </p>
    </div>
  );
}
