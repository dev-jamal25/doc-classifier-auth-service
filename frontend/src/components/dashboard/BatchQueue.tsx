import { ArrowUpRight, Clock3 } from "lucide-react";
import { Link } from "react-router-dom";
import type { Batch } from "../../types";
import { formatDateTime } from "../../lib/format";
import { Card } from "../ui/Card";
import { StatusBadge } from "../ui/StatusBadge";

export function BatchQueue({ batches, className }: { batches: Batch[]; className?: string }) {
  return (
    <Card
      className={className}
      contentClassName="space-y-3"
      eyebrow="Ingestion"
      icon={<Clock3 className="h-5 w-5" aria-hidden="true" />}
      title="Batch queue"
    >
      <div className="space-y-3">
        {batches.map((batch) => (
          <Card as="article" key={batch.id} variant="interactive">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex min-h-7 flex-wrap items-center gap-2">
                  <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">{batch.sourceFilename}</h3>
                  <StatusBadge state={batch.state} />
                </div>
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                  {formatDateTime(batch.updatedAt)} by {batch.sftpUser}
                </p>
              </div>

              <Link
                aria-label={`Open ${batch.sourceFilename}`}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-200 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-500 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white"
                to={`/batches/${batch.id}`}
              >
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="mt-4">
              <div className="mb-2 flex justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
                <span>{batch.documentCount} documents</span>
                <span>{batch.progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-ocean-600 to-mint-500"
                  style={{ width: `${batch.progress}%` }}
                />
              </div>
            </div>

            {batch.lowConfidenceCount > 0 ? (
              <p className="mt-3 text-xs font-semibold text-amber-700 dark:text-amber-200">
                {batch.lowConfidenceCount} low-confidence predictions
              </p>
            ) : null}
          </Card>
        ))}
      </div>
    </Card>
  );
}
