import { CheckCircle2, LockKeyhole, PencilLine } from "lucide-react";
import { Link } from "react-router-dom";
import { REVIEW_THRESHOLD } from "../../lib/mockData";
import { formatPercent, labelToTitle } from "../../lib/format";
import type { Prediction, Role } from "../../types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { DocumentPreview } from "./DocumentPreview";

export function PredictionReviewPanel({
  predictions,
  activeRole,
  className,
}: {
  predictions: Prediction[];
  activeRole: Role;
  className?: string;
}) {
  const reviewable = predictions.filter((prediction) => prediction.confidence < REVIEW_THRESHOLD);
  const featured = reviewable[0] ?? predictions[0];
  const canRelabel = activeRole === "reviewer";

  return (
    <Card
      action={
        <Link
          className="text-sm font-semibold text-ocean-700 hover:text-ocean-600 dark:text-sky-300 dark:hover:text-sky-200"
          to="/predictions/review"
        >
          Open queue
        </Link>
      }
      className={className}
      eyebrow="Classifier output"
      icon={<PencilLine className="h-5 w-5" aria-hidden="true" />}
      title="Prediction review"
    >
      <div className="grid gap-5 lg:grid-cols-12">
        <div className="lg:col-span-4 xl:col-span-3">
          <DocumentPreview label={featured.label} />
        </div>

        <div className="min-w-0 lg:col-span-8 xl:col-span-9">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-xl font-bold text-slate-950 dark:text-white">{labelToTitle(featured.label)}</h3>
                <Badge tone={featured.confidence < REVIEW_THRESHOLD ? "amber" : "green"}>
                  {formatPercent(featured.confidence)} confidence
                </Badge>
              </div>
              <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
                {featured.sourceFilename} from {featured.batchId}
              </p>
            </div>

            {canRelabel ? (
              <Button icon={<PencilLine className="h-4 w-4" aria-hidden="true" />} type="button">
                Relabel
              </Button>
            ) : (
              <Button
                disabled
                icon={<LockKeyhole className="h-4 w-4" aria-hidden="true" />}
                type="button"
                variant="secondary"
              >
                Read only
              </Button>
            )}
          </div>

          <div className="mt-6 space-y-3">
            {featured.top5.map((candidate) => (
              <div key={candidate.label}>
                <div className="mb-1.5 flex justify-between text-sm font-semibold">
                  <span className="text-slate-700 dark:text-slate-200">{labelToTitle(candidate.label)}</span>
                  <span className="text-slate-500 dark:text-slate-400">{formatPercent(candidate.confidence)}</span>
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

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {reviewable.map((prediction) => (
              <Card as="article" className="p-4" key={prediction.id} variant="subtle">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-bold text-slate-950 dark:text-white">
                    {prediction.sourceFilename}
                  </p>
                  {prediction.reviewedLabel ? (
                    <CheckCircle2 className="h-4 w-4 text-mint-500" aria-label="Reviewed" />
                  ) : null}
                </div>
                <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {labelToTitle(prediction.label)} at {formatPercent(prediction.confidence)}
                </p>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
