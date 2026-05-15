import { cn } from "../../lib/styles";
import type { DocumentLabel } from "../../types";
import { Card } from "../ui/Card";

export function DocumentPreview({ label }: { label: DocumentLabel }) {
  const rows = label === "invoice" ? [88, 72, 92, 64, 84, 76] : [74, 96, 68, 88, 58, 82];

  return (
    <Card
      as="div"
      aria-label={`${label} document preview`}
      className="relative aspect-[4/5] overflow-hidden p-4 shadow-inner dark:bg-slate-950"
      role="img"
      variant="subtle"
    >
      <div className="mb-5 flex items-center justify-between">
        <div className="h-3 w-20 rounded-full bg-slate-300 dark:bg-slate-700" />
        <div className="h-8 w-8 rounded-lg border border-slate-200 bg-slate-100 dark:border-white/10 dark:bg-white/10" />
      </div>

      <div className="space-y-2">
        {rows.map((width, index) => (
          <div
            className={cn(
              "h-2 rounded-full bg-slate-200 dark:bg-slate-700",
              index === 2 ? "bg-ocean-200 dark:bg-sky-400/40" : "",
            )}
            key={`${width}-${index}`}
            style={{ width: `${width}%` }}
          />
        ))}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <div className="h-8 rounded-lg bg-slate-100 dark:bg-white/10" key={index} />
        ))}
      </div>

      <div className="absolute bottom-3 left-3 right-3 rounded-xl bg-slate-950/90 px-3 py-2 text-xs font-semibold text-white">
        {label.split("_").join(" ")}
      </div>
    </Card>
  );
}
