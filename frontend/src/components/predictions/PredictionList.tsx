import { BrainCircuit, CheckCircle2 } from "lucide-react";
import type { Prediction } from "../../types";
import { formatDateTime, formatPercent, labelToTitle } from "../../lib/format";
import { REVIEW_THRESHOLD } from "../../lib/mockData";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

export function PredictionList({
  predictions,
  className,
  title = "Predictions",
}: {
  predictions: Prediction[];
  className?: string;
  title?: string;
}) {
  return (
    <Card
      className={className}
      eyebrow="Classifier output"
      icon={<BrainCircuit className="h-5 w-5" aria-hidden="true" />}
      title={title}
    >
      <div className="space-y-3">
        {predictions.map((prediction) => (
          <Card as="article" className="p-4" key={prediction.id} variant="subtle">
            <div className="grid gap-4 md:grid-cols-12 md:items-center">
              <div className="min-w-0 md:col-span-6">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">
                    {prediction.sourceFilename}
                  </h3>
                  {prediction.reviewedLabel ? (
                    <CheckCircle2 className="h-4 w-4 text-mint-500" aria-label="Reviewed" />
                  ) : null}
                </div>
                <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {formatDateTime(prediction.createdAt)}
                </p>
              </div>

              <div className="md:col-span-3">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Predicted label</p>
                <p className="mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {labelToTitle(prediction.label)}
                </p>
              </div>

              <div className="flex justify-start md:col-span-3 md:justify-end">
                <Badge tone={prediction.confidence < REVIEW_THRESHOLD ? "amber" : "green"}>
                  {formatPercent(prediction.confidence)}
                </Badge>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </Card>
  );
}
