import type { PriorityLevel } from "@/lib/types";

const DOT: Record<PriorityLevel, string> = {
  rojo: "🔴",
  amarillo: "🟡",
  verde: "🟢",
};

export function PriorityBadge({ priority }: { priority: PriorityLevel }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs" title={`Prioridad: ${priority}`}>
      {DOT[priority]}
    </span>
  );
}
