import { LockKeyhole, PencilLine } from "lucide-react";
import type { Prediction, Role } from "../../types";
import { formatPercent, labelToTitle } from "../../lib/format";
import { DOCUMENT_LABELS, REVIEW_THRESHOLD } from "../../lib/mockData";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { DocumentPreview } from "../dashboard/DocumentPreview";

export function ReviewQueue({
  predictions,
  activeRole,
  className,
}: {
  predictions: Prediction[];
  activeRole: Role;
  className?: string;
}) {
  const reviewable = predictions.filter((prediction) => prediction.confidence < REVIEW_THRESHOLD);
  const canRelabel = activeRole === "reviewer";

  return (
    <Card
      className={className}
      eyebrow="Human review"
      icon={<PencilLine className="h-5 w-5" aria-hidden="true" />}
      title="Low-confidence queue"
    >
      <div className="space-y-4">
        {reviewable.length ? (
          reviewable.map((prediction) => (
          <Card as="article" className="p-4" key={prediction.id} variant="interactive">
            <div className="grid gap-5 md:grid-cols-12">
              <div className="md:col-span-3">
                <DocumentPreview label={prediction.label} />
              </div>
              <div className="min-w-0 md:col-span-9">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-bold text-slate-950 dark:text-white">
                        {labelToTitle(prediction.label)}
                      </h3>
                      <Badge tone="amber">{formatPercent(prediction.confidence)} confidence</Badge>
                    </div>
                    <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
                      {prediction.sourceFilename} from {prediction.batchId}
                    </p>
                  </div>

                  {canRelabel ? (
                    <Button icon={<PencilLine className="h-4 w-4" aria-hidden="true" />} type="button">
                      Mark reviewed
                    </Button>
                  ) : (
                    <Button
                      disabled
                      icon={<LockKeyhole className="h-4 w-4" aria-hidden="true" />}
                      type="button"
                      variant="secondary"
                    >
                      Reviewer only
                    </Button>
                  )}
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {prediction.top5.slice(0, 4).map((candidate) => (
                    <div key={candidate.label}>
                      <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
                        <span>{labelToTitle(candidate.label)}</span>
                        <span>{formatPercent(candidate.confidence)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-ocean-600 to-mint-500"
                          style={{ width: `${candidate.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                  <label className="grid gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Reviewed label
                    <select
                      className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-900 outline-none transition focus:border-ocean-500 focus:ring-4 focus:ring-ocean-500/15 disabled:cursor-not-allowed disabled:opacity-70 dark:border-white/10 dark:bg-slate-950 dark:text-white"
                      defaultValue={prediction.reviewedLabel ?? prediction.label}
                      disabled={!canRelabel}
                    >
                      {DOCUMENT_LABELS.map((label) => (
                        <option key={label} value={label}>
                          {labelToTitle(label)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <Button
                    disabled={!canRelabel}
                    icon={
                      canRelabel ? (
                        <PencilLine className="h-4 w-4" aria-hidden="true" />
                      ) : (
                        <LockKeyhole className="h-4 w-4" aria-hidden="true" />
                      )
                    }
                    type="button"
                    variant={canRelabel ? "primary" : "secondary"}
                  >
                    Relabel
                  </Button>
                </div>
              </div>
            </div>
          </Card>
          ))
        ) : (
          <Card as="div" className="p-4" variant="subtle">
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">No predictions need review.</p>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              New items will appear here when mock classifier confidence is below 70%.
            </p>
          </Card>
        )}
      </div>
    </Card>
  );
}
