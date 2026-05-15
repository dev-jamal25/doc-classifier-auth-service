import { ArrowUpRight, Clock3, FolderInput } from "lucide-react";
import { Link } from "react-router-dom";
import type { Batch, Prediction } from "../../types";
import { formatDateTime, formatPercent, labelToTitle } from "../../lib/format";
import { REVIEW_THRESHOLD } from "../../lib/mockData";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { StatusBadge } from "../ui/StatusBadge";

const getReviewStatus = (batch: Batch, prediction?: Prediction) => {
  if (batch.state === "failed") {
    return { label: "Failed", tone: "rose" as const };
  }
  if (!prediction) {
    return { label: "Waiting", tone: "slate" as const };
  }
  if (prediction.reviewedLabel) {
    return { label: "Reviewed", tone: "green" as const };
  }
  if (prediction.confidence < REVIEW_THRESHOLD) {
    return { label: "Needs review", tone: "amber" as const };
  }
  return { label: "Auto accepted", tone: "green" as const };
};

export function BatchList({
  batches,
  predictions,
  className,
}: {
  batches: Batch[];
  predictions: Prediction[];
  className?: string;
}) {
  return (
    <Card
      className={className}
      eyebrow="SFTP results"
      icon={<FolderInput className="h-5 w-5" aria-hidden="true" />}
      title="Ingested batches"
    >
      <div className="space-y-3">
        {batches.map((batch) => {
          const prediction = predictions.find((item) => item.batchId === batch.id);
          const reviewStatus = getReviewStatus(batch, prediction);

          return (
            <Card as="article" className="p-4" key={batch.id} variant="interactive">
              <div className="grid gap-4 md:grid-cols-12 md:items-center">
                <div className="min-w-0 md:col-span-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">{batch.sourceFilename}</h3>
                  <StatusBadge state={batch.state} />
                </div>
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                  Created {formatDateTime(batch.createdAt)}
                </p>
              </div>

              <div className="md:col-span-2">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Source</p>
                <p className="mt-1 truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{batch.source}</p>
                <p className="mt-0.5 truncate text-xs font-medium text-slate-500 dark:text-slate-400">{batch.sftpUser}</p>
              </div>

              <div className="md:col-span-2">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Prediction</p>
                <p className="mt-1 truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {prediction ? labelToTitle(prediction.label) : "Pending"}
                </p>
                <p className="mt-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {prediction ? formatPercent(prediction.confidence) : "Awaiting worker"}
                </p>
              </div>

              <div className="flex flex-wrap gap-2 md:col-span-3 md:justify-end">
                <Badge tone="slate">{batch.documentCount} docs</Badge>
                <Badge tone={reviewStatus.tone}>{reviewStatus.label}</Badge>
              </div>

              <Link
                aria-label={`Open ${batch.sourceFilename}`}
                className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-white text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-500 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/15 dark:hover:text-white"
                to={`/batches/${batch.id}`}
              >
                <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </Card>
          );
        })}
      </div>
    </Card>
  );
}
