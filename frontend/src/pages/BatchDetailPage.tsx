import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, FolderInput } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { AuditTimeline } from "../components/dashboard/AuditTimeline";
import { BatchDetailSummary } from "../components/batches/BatchDetailSummary";
import { BatchPredictionDetail } from "../components/batches/BatchPredictionDetail";
import { Card } from "../components/ui/Card";
import { useAuth } from "../lib/auth";
import { mockAuditLog, mockBatches, mockPredictions } from "../lib/mockData";

export function BatchDetailPage() {
  const { batchId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  const activeRole = user.roles[0] ?? "admin";
  const batch = mockBatches.find((item) => item.id === batchId);
  const predictions = mockPredictions.filter((prediction) => prediction.batchId === batchId);
  const predictionIds = new Set(predictions.map((prediction) => prediction.id));
  const history = mockAuditLog.filter(
    (entry) => entry.targetId === batchId || predictionIds.has(entry.targetId),
  );

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <AppShell activeRole={activeRole} onLogout={handleLogout} user={user}>
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 gap-6 lg:grid-cols-12"
        initial={{ opacity: 0, y: 10 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <PageHeader
          action={
            <Link
              className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-500 dark:border-white/10 dark:bg-white/10 dark:text-slate-200 dark:hover:bg-white/15"
              to="/batches"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Batches
            </Link>
          }
          description="Batch detail mirrors backend read models: ingestion metadata, state, and predictions produced by the worker."
          eyebrow="Batch"
          title={batch ? batch.sourceFilename : "Batch not found"}
        />

        {batch ? (
          <>
            <BatchDetailSummary batch={batch} className="lg:col-span-4" />
            <BatchPredictionDetail className="lg:col-span-8" prediction={predictions[0]} />
            <AuditTimeline className="lg:col-span-12" entries={history} />
          </>
        ) : (
          <Card
            className="lg:col-span-12"
            eyebrow="Missing mock record"
            icon={<FolderInput className="h-5 w-5" aria-hidden="true" />}
            title="No batch found"
          >
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              The mock dataset does not include a batch with ID `{batchId}`.
            </p>
          </Card>
        )}
      </motion.div>
    </AppShell>
  );
}
