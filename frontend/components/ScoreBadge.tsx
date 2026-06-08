import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number | null;
  className?: string;
}

export default function ScoreBadge({ score, className }: ScoreBadgeProps) {
  if (score === null) return <span className={cn("text-gray-600 text-xs", className)}>—</span>;

  const style =
    score >= 80
      ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/25"
      : score >= 60
      ? "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/25"
      : score >= 40
      ? "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/25"
      : "bg-red-500/15 text-red-400 ring-1 ring-red-500/25";

  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold tabular-nums", style, className)}>
      {score}
    </span>
  );
}
