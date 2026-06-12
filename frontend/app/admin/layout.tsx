"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { usePlan } from "@/hooks/usePlan";
import { useAuth } from "@/hooks/useAuth";

const ADMIN_NAV = [
  {
    href: "/admin",
    label: "Visão geral",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
      </svg>
    ),
  },
  {
    href: "/admin/usuarios",
    label: "Usuários",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    href: "/admin/planos",
    label: "Planos",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
  },
  {
    href: "/admin/duplicatas",
    label: "Duplicatas",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    href: "/admin/auditoria",
    label: "Auditoria",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { role, isLoading: planLoading } = usePlan();

  const loading = authLoading || planLoading;

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (role && role !== "admin") {
      router.replace("/dashboard");
    }
  }, [user, role, loading, router]);

  if (loading || !user || (role && role !== "admin")) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-950">
      {/* Sidebar Admin */}
      <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Header */}
        <div className="px-4 py-4 border-b border-gray-800">
          <Link href="/dashboard" className="flex items-center gap-2 text-gray-500 hover:text-gray-300 text-xs transition-colors mb-3">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Voltar ao app
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-red-600/20 border border-red-500/30 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-semibold text-white leading-none">Painel Admin</p>
              <p className="text-[10px] text-red-400/70 mt-0.5">Radar Imóvel</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {ADMIN_NAV.map(({ href, label, icon }) => {
            const active = href === "/admin" ? pathname === "/admin" : pathname?.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-red-500/10 text-red-400 font-medium"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                }`}
              >
                <span className={active ? "text-red-400" : "text-gray-500"}>{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Conteúdo */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
