import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number | null;
  className?: string;
}

export default function ScoreBadge({ score, className }: ScoreBadgeProps) {
  if (score === null) return <span className={cn("text-gray-400 text-sm", className)}>—</span>;

  const color =
    score >= 90 ? "bg-green-100 text-green-800" :
    score >= 70 ? "bg-yellow-100 text-yellow-800" :
                  "bg-red-100 text-red-800";

  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold", color, className)}>
      {score}
    </span>
  );
}
