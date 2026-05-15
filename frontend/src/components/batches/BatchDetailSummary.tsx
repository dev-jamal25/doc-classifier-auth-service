import { AlertTriangle, CheckCircle2, Clock3, FolderInput } from "lucide-react";
import type { Batch } from "../../types";
import { formatDateTime } from "../../lib/format";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { StatusBadge } from "../ui/StatusBadge";

export function BatchDetailSummary({ batch, className }: { batch: Batch; className?: string }) {
  const items = [
    { label: "Documents", value: batch.documentCount.toString(), icon: FolderInput },
    { label: "Progress", value: `${batch.progress}%`, icon: CheckCircle2 },
    { label: "Needs review", value: batch.lowConfidenceCount.toString(), icon: AlertTriangle },
  ];

  return (
    <Card
      className={className}
      eyebrow="Batch detail"
      icon={<FolderInput className="h-5 w-5" aria-hidden="true" />}
      title={batch.sourceFilename}
    >
      <div className="flex flex-wrap gap-2">
        <StatusBadge state={batch.state} />
        <Badge tone="slate">{batch.source}</Badge>
        <Badge tone="blue">{batch.sftpUser}</Badge>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {items.map((item) => (
          <Card as="div" className="p-4" key={item.label} variant="subtle">
            <item.icon className="h-5 w-5 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
            <p className="mt-3 text-2xl font-bold text-slate-950 dark:text-white">{item.value}</p>
            <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">{item.label}</p>
          </Card>
        ))}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Created</p>
          <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
            <Clock3 className="h-4 w-4 text-slate-400" aria-hidden="true" />
            {formatDateTime(batch.createdAt)}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Updated</p>
          <p className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
            <Clock3 className="h-4 w-4 text-slate-400" aria-hidden="true" />
            {formatDateTime(batch.updatedAt)}
          </p>
        </div>
      </div>

      <Card as="div" className="mt-5 p-4" variant="subtle">
        <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Request ID</p>
        <p className="mt-1 break-all text-sm font-semibold text-slate-800 dark:text-slate-100">{batch.requestId}</p>
      </Card>

      {batch.failureReason ? (
        <Card as="div" className="mt-5 p-4" variant="subtle">
          <p className="text-sm font-semibold text-rose-700 dark:text-rose-200">Failure reason</p>
          <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{batch.failureReason}</p>
        </Card>
      ) : null}
    </Card>
  );
}
