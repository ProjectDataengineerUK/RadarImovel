"use client";

import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import Link from "next/link";
import type { Property } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import ScoreBadge from "./ScoreBadge";

const columns: ColumnDef<Property>[] = [
  {
    accessorKey: "opportunity_score",
    header: "Score",
    cell: ({ getValue }) => <ScoreBadge score={getValue() as number | null} />,
    size: 64,
  },
  {
    accessorKey: "bank_name",
    header: "Fonte",
    cell: ({ getValue }) => {
      const v = getValue() as string | null;
      return <span className="text-xs text-gray-500 whitespace-nowrap">{v ?? "—"}</span>;
    },
  },
  {
    accessorFn: (r) => `${r.city}/${r.state}`,
    id: "location",
    header: "Cidade/UF",
    cell: ({ row }) => (
      <Link href={`/imoveis/${row.original.id}`} className="font-medium hover:underline">
        {row.original.city}/{row.original.state}
      </Link>
    ),
  },
  { accessorKey: "property_type", header: "Tipo" },
  { accessorKey: "sale_modality", header: "Modalidade" },
  {
    accessorKey: "current_value",
    header: "Preço",
    cell: ({ getValue }) => formatCurrency(getValue() as number),
  },
  {
    accessorKey: "discount_percent",
    header: "Desconto",
    cell: ({ getValue }) => {
      const v = getValue() as number | null;
      return v ? <span className="text-green-600 font-medium">{v}%</span> : "—";
    },
  },
  { accessorKey: "occupancy_status", header: "Situação" },
  {
    accessorKey: "auction_date",
    header: "Leilão",
    cell: ({ getValue }) => {
      const v = getValue() as string | null;
      return v ? formatDate(v) : "—";
    },
  },
  {
    accessorKey: "last_seen_at",
    header: "Atualizado",
    cell: ({ getValue }) => {
      const v = getValue() as string | null;
      return v ? (
        <span className="text-xs text-gray-400">{formatDate(v)}</span>
      ) : "—";
    },
  },
];

interface PropertyTableProps {
  properties: Property[];
}

export default function PropertyTable({ properties }: PropertyTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data: properties,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th
                  key={h.id}
                  onClick={h.column.getToggleSortingHandler()}
                  className="px-4 py-3 text-left font-semibold text-gray-600 cursor-pointer select-none whitespace-nowrap"
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {h.column.getIsSorted() === "asc" ? " ↑" : h.column.getIsSorted() === "desc" ? " ↓" : ""}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b hover:bg-gray-50">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {properties.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">
                Nenhum imóvel encontrado.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
