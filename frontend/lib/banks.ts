export const BANK_DISPLAY: Record<string, { label: string; color: string; bg: string }> = {
  caixa:    { label: "Caixa",    color: "text-sky-400",    bg: "bg-sky-500/10 ring-sky-500/20" },
  bb:       { label: "BB",       color: "text-yellow-400", bg: "bg-yellow-500/10 ring-yellow-500/20" },
  brb:      { label: "BRB",      color: "text-purple-400", bg: "bg-purple-500/10 ring-purple-500/20" },
  bnb:      { label: "BNB",      color: "text-orange-400", bg: "bg-orange-500/10 ring-orange-500/20" },
  basa:     { label: "BASA",     color: "text-emerald-400",bg: "bg-emerald-500/10 ring-emerald-500/20" },
  banrisul: { label: "BRSUL",    color: "text-red-400",    bg: "bg-red-500/10 ring-red-500/20" },
  banestes: { label: "BANES",    color: "text-teal-400",   bg: "bg-teal-500/10 ring-teal-500/20" },
};

export const BANK_OPTIONS = [
  { value: "caixa",    label: "Caixa Econômica" },
  { value: "bb",       label: "Banco do Brasil" },
  { value: "brb",      label: "BRB" },
  { value: "bnb",      label: "Banco do Nordeste" },
  { value: "basa",     label: "Banco da Amazônia" },
  { value: "banrisul", label: "Banrisul" },
  { value: "banestes", label: "Banestes" },
];
