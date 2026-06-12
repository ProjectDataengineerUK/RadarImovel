"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { KanbanBoard, type PortfolioItem } from "@/components/KanbanBoard";
import { FeatureGate } from "@/components/FeatureGate";

export default function CarteiraPage() {
  return (
    <FeatureGate feature="portfolio" fallback={
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <p className="text-lg font-medium mb-2">Carteira Kanban</p>
          <p className="text-sm">Disponível nos planos Pro e Premium.</p>
        </div>
      </div>
    }>
      <CarteiraContent />
    </FeatureGate>
  );
}

function CarteiraContent() {
  const { data, isLoading, isError } = useQuery<{ items: PortfolioItem[] }>({
    queryKey: ["portfolio"],
    queryFn: () => api.get("/portfolio").then((r) => r.data),
  });

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Minha Carteira</h1>
        <p className="text-sm text-gray-400">
          Adicione imóveis da lista para acompanhar aqui
        </p>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {isError && (
        <div className="text-center text-red-500 py-8">Erro ao carregar carteira.</div>
      )}

      {data && data.items.length === 0 && (
        <div className="text-center text-gray-400 py-12">
          <p className="text-4xl mb-4">📋</p>
          <p className="font-medium">Sua carteira está vazia.</p>
          <p className="text-sm mt-1">Na página de um imóvel, clique em "Adicionar à Carteira".</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <KanbanBoard items={data.items} />
      )}
    </div>
  );
}
