import { History, RotateCcw, ShieldCheck } from "lucide-react";
import type { AuditLogEntry } from "../../types";
import { formatDateTime, labelToTitle } from "../../lib/format";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

const actionIcon = {
  role_change: ShieldCheck,
  relabel: RotateCcw,
  batch_state_change: History,
} as const;

export function AuditTimeline({ entries, className }: { entries: AuditLogEntry[]; className?: string }) {
  return (
    <Card
      className={className}
      eyebrow="Traceability"
      icon={<History className="h-5 w-5" aria-hidden="true" />}
      title="Audit timeline"
    >
      {entries.length ? (
        <div className="space-y-4">
        {entries.map((entry) => {
          const Icon = actionIcon[entry.action];

          return (
            <article className="relative flex gap-3" key={entry.id}>
              <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white dark:bg-white dark:text-ink-950">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <Card as="div" className="min-w-0 flex-1 p-4" variant="subtle">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge tone="slate">{labelToTitle(entry.action)}</Badge>
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    {formatDateTime(entry.createdAt)}
                  </span>
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-950 dark:text-white">
                  {entry.actorEmail ?? "System worker"}
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  {entry.beforeValue} to {entry.afterValue}
                </p>
              </Card>
            </article>
          );
        })}
        </div>
      ) : (
        <Card as="div" className="p-4" variant="subtle">
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            No audit or review history is attached to this mock record yet.
          </p>
        </Card>
      )}
    </Card>
  );
}
