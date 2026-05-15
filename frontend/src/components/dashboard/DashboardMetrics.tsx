import { Activity, BrainCircuit, FileStack, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";
import type { AuditLogEntry, Batch, Prediction } from "../../types";
import { Card } from "../ui/Card";

export function DashboardMetrics({
  batches,
  predictions,
  auditLog,
}: {
  batches: Batch[];
  predictions: Prediction[];
  auditLog: AuditLogEntry[];
}) {
  const lowConfidence = predictions.filter((prediction) => prediction.confidence < 0.7).length;
  const activeBatches = batches.filter((batch) => batch.state === "processing" || batch.state === "pending").length;
  const completedDocuments = batches
    .filter((batch) => batch.state === "completed")
    .reduce((total, batch) => total + batch.documentCount, 0);

  const metrics = [
    {
      label: "Active batches",
      value: activeBatches.toString(),
      icon: FileStack,
      detail: "SFTP drops in flight",
    },
    {
      label: "Review queue",
      value: lowConfidence.toString(),
      icon: BrainCircuit,
      detail: "Below 70% confidence",
    },
    {
      label: "Completed docs",
      value: completedDocuments.toString(),
      icon: Activity,
      detail: "Classified in recent batches",
    },
    {
      label: "Audit events",
      value: auditLog.length.toString(),
      icon: ShieldCheck,
      detail: "Sensitive actions tracked",
    },
  ];

  return (
    <>
      {metrics.map((metric, index) => (
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-3"
          initial={{ opacity: 0, y: 12 }}
          key={metric.label}
          transition={{ delay: index * 0.04, duration: 0.35 }}
        >
          <Card icon={<metric.icon className="h-5 w-5" aria-hidden="true" />} title={metric.label} variant="metric">
            <p className="text-3xl font-bold text-slate-950 dark:text-white">{metric.value}</p>
            <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{metric.detail}</p>
          </Card>
        </motion.div>
      ))}
    </>
  );
}
