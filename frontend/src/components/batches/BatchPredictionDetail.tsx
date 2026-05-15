import { BrainCircuit, CheckCircle2 } from "lucide-react";
import type { Prediction } from "../../types";
import { formatDateTime, formatPercent, labelToTitle } from "../../lib/format";
import { REVIEW_THRESHOLD } from "../../lib/mockData";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { DocumentPreview } from "../dashboard/DocumentPreview";

export function BatchPredictionDetail({
  prediction,
  className,
}: {
  prediction?: Prediction;
  className?: string;
}) {
  return (
    <Card
      className={className}
      eyebrow="Prediction result"
      icon={<BrainCircuit className="h-5 w-5" aria-hidden="true" />}
      title={prediction ? labelToTitle(prediction.label) : "Awaiting prediction"}
    >
      {prediction ? (
        <div className="grid gap-5 lg:grid-cols-12">
          <div className="lg:col-span-4 xl:col-span-3">
            <DocumentPreview label={prediction.label} />
          </div>

          <div className="min-w-0 lg:col-span-8 xl:col-span-9">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-xl font-bold text-slate-950 dark:text-white">
                    {labelToTitle(prediction.label)}
                  </h3>
                  <Badge tone={prediction.confidence < REVIEW_THRESHOLD ? "amber" : "green"}>
                    {formatPercent(prediction.confidence)} confidence
                  </Badge>
                  <Badge tone={prediction.reviewedLabel ? "green" : "slate"}>
                    {prediction.reviewedLabel ? "Reviewed" : "Not reviewed"}
                  </Badge>
                </div>
                <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
                  {prediction.sourceFilename} created {formatDateTime(prediction.createdAt)}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {prediction.top5.map((candidate) => (
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

            {prediction.reviewedLabel ? (
              <Card as="div" className="mt-5 p-4" variant="subtle">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-mint-500" aria-hidden="true" />
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    Reviewed as {labelToTitle(prediction.reviewedLabel)}
                  </p>
                </div>
              </Card>
            ) : null}
          </div>
        </div>
      ) : (
        <Card as="div" className="p-4" variant="subtle">
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            The worker has not written a prediction for this mock batch yet.
          </p>
        </Card>
      )}
    </Card>
  );
}
