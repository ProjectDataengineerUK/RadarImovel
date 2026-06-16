import type { Metadata } from "next";
import LandingPage from "@/components/LandingPage";

export const metadata: Metadata = {
  title: "Mastavista — Inteligência em Leilões Imobiliários",
  description:
    "Monitore leilões da Caixa, BB, BRB e mais 13 fontes. Alertas em tempo real, leitura de editais com IA, score de oportunidade e calculadora de ROI.",
  keywords: ["leilão imóvel", "leilão caixa", "hasta judicial", "imóvel barato", "mastavista"],
  openGraph: {
    title: "Mastavista — Inteligência em Leilões Imobiliários",
    description:
      "16 fontes monitoradas. Alertas antes do mercado. Leia editais com IA e calcule o ROI em segundos.",
    url: "https://mastavista.com.br",
    siteName: "Mastavista",
    locale: "pt_BR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Mastavista — Inteligência em Leilões Imobiliários",
    description: "16 fontes monitoradas. Alertas antes do mercado. Edital lido por IA.",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  metadataBase: new URL("https://mastavista.com.br"),
};

export default function Page() {
  return <LandingPage />;
}
