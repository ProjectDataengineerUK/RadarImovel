"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";

const AUTH_ROUTES = ["/login", "/register"];

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/imoveis", label: "Imóveis" },
  { href: "/alertas", label: "Alertas" },
  { href: "/configuracoes", label: "Configurações" },
  { href: "/admin", label: "Admin" },
];

function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 min-h-screen bg-gray-900 border-r border-gray-800 flex flex-col py-6 px-4 shrink-0">
      <div className="mb-8">
        <span className="text-white font-bold text-lg tracking-tight">Radar Imóvel</span>
        <span className="block text-gray-500 text-xs mt-0.5">Monitor de leilões</span>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label }) => {
          const active = path === href || path?.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-blue-600 text-white font-medium"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const pathname = usePathname();
  const isAuthRoute = AUTH_ROUTES.some((r) => pathname?.startsWith(r));

  return (
    <html lang="pt-BR" className="dark">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <QueryClientProvider client={queryClient}>
          <div className="flex min-h-screen">
            {!isAuthRoute && <Sidebar />}
            <main className="flex-1 overflow-auto">{children}</main>
          </div>
        </QueryClientProvider>
      </body>
    </html>
  );
}
