export const BANK_DISPLAY: Record<string, { label: string; color: string; bg: string }> = {
  // Bancos públicos
  caixa:    { label: "Caixa",    color: "text-sky-400",    bg: "bg-sky-500/10 ring-sky-500/20" },
  bb:       { label: "BB",       color: "text-yellow-400", bg: "bg-yellow-500/10 ring-yellow-500/20" },
  brb:      { label: "BRB",      color: "text-purple-400", bg: "bg-purple-500/10 ring-purple-500/20" },
  bnb:      { label: "BNB",      color: "text-orange-400", bg: "bg-orange-500/10 ring-orange-500/20" },
  basa:     { label: "BASA",     color: "text-emerald-400",bg: "bg-emerald-500/10 ring-emerald-500/20" },
  banrisul: { label: "BRSUL",    color: "text-red-400",    bg: "bg-red-500/10 ring-red-500/20" },
  banestes: { label: "BANES",    color: "text-teal-400",   bg: "bg-teal-500/10 ring-teal-500/20" },
  // Leiloeiros
  mega:     { label: "Mega",     color: "text-violet-400", bg: "bg-violet-500/10 ring-violet-500/20" },
  zuk:      { label: "Zuk",      color: "text-pink-400",   bg: "bg-pink-500/10 ring-pink-500/20" },
  sodre:    { label: "Sodré",    color: "text-amber-400",  bg: "bg-amber-500/10 ring-amber-500/20" },
  frazao:   { label: "Frazão",   color: "text-lime-400",   bg: "bg-lime-500/10 ring-lime-500/20" },
  fidalgo:  { label: "Fidalgo",  color: "text-cyan-400",   bg: "bg-cyan-500/10 ring-cyan-500/20" },
  tjsp:     { label: "TJ-SP",    color: "text-rose-400",   bg: "bg-rose-500/10 ring-rose-500/20" },
};

export const BANK_OPTIONS = [
  { value: "caixa",    label: "Caixa Econômica" },
  { value: "bb",       label: "Banco do Brasil" },
  { value: "brb",      label: "BRB" },
  { value: "bnb",      label: "Banco do Nordeste" },
  { value: "basa",     label: "Banco da Amazônia" },
  { value: "banrisul", label: "Banrisul" },
  { value: "banestes", label: "Banestes" },
  { value: "mega",     label: "Mega Leilões" },
  { value: "zuk",      label: "Portal Zuk" },
  { value: "sodre",    label: "Sodré Santoro" },
  { value: "frazao",   label: "Frazão Leilões" },
  { value: "fidalgo",  label: "Fidalgo Leilões" },
  { value: "tjsp",     label: "TJ-SP Hasta Pública" },
];
