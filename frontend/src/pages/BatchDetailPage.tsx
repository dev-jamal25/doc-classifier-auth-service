import { useEffect, useState } from "react";
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
import {
  API_ENDPOINTS,
  type ApiBatch,
  type ApiPrediction,
  mapBatch,
  mapPrediction,
} from "../lib/api";
import { apiGet } from "../lib/apiClient";
import { mockAuditLog, mockBatches, mockPredictions } from "../lib/mockData";
import type { AuditLogEntry, Batch, Prediction } from "../types";

export function BatchDetailPage() {
  const { batchId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [batch, setBatch] = useState<Batch | undefined>(() =>
    mockBatches.find((item) => item.id === batchId),
  );
  const [predictions, setPredictions] = useState<Prediction[]>(
    mockPredictions.filter((p) => p.batchId === batchId),
  );
  const [auditLog] = useState<AuditLogEntry[]>(mockAuditLog);

  useEffect(() => {
    if (!batchId) return;
    apiGet<ApiBatch>(API_ENDPOINTS.batchDetail(batchId))
      .then((raw) => setBatch(mapBatch(raw)))
      .catch(() => {});
  }, [batchId]);

  useEffect(() => {
    apiGet<{ items: ApiPrediction[] }>(API_ENDPOINTS.recentPredictions)
      .then((data) => {
        const mapped = data.items.map(mapPrediction).filter((p) => p.batchId === batchId);
        if (mapped.length > 0) {
          setPredictions(mapped);
        }
      })
      .catch(() => {});
  }, [batchId]);

  if (!user) {
    return null;
  }

  const activeRole = user.roles[0] ?? "admin";
  const predictionIds = new Set(predictions.map((p) => p.id));
  const history = auditLog.filter(
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
            eyebrow="Not found"
            icon={<FolderInput className="h-5 w-5" aria-hidden="true" />}
            title="No batch found"
          >
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              No batch with ID `{batchId}` was found.
            </p>
          </Card>
        )}
      </motion.div>
    </AppShell>
  );
}
