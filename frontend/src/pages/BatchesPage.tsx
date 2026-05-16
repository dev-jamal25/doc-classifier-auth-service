import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FolderInput, RadioTower, ServerCog } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { BatchList } from "../components/batches/BatchList";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useAuth } from "../lib/auth";
import { API_ENDPOINTS, type ApiBatch, type ApiPrediction, mapBatch, mapPrediction } from "../lib/api";
import { apiGet } from "../lib/apiClient";
import { mockBatches, mockPredictions } from "../lib/mockData";
import type { Batch, Prediction } from "../types";

export function BatchesPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [batches, setBatches] = useState<Batch[]>(mockBatches);
  const [predictions, setPredictions] = useState<Prediction[]>(mockPredictions);

  useEffect(() => {
    apiGet<{ items: ApiBatch[] }>(API_ENDPOINTS.batches)
      .then((data) => setBatches(data.items.map(mapBatch)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    apiGet<{ items: ApiPrediction[] }>(API_ENDPOINTS.recentPredictions)
      .then((data) => setPredictions(data.items.map(mapPrediction)))
      .catch(() => {});
  }, []);

  if (!user) {
    return null;
  }

  const activeRole = user.roles[0] ?? "admin";
  const activeBatches = batches.filter((batch) => batch.state === "pending" || batch.state === "processing");

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
          action={<Badge tone="green">{activeBatches.length} active</Badge>}
          description="Batches appear here after scanner-vendor TIFFs land in SFTP and the ingestion worker creates backend records."
          eyebrow="SFTP ingestion"
          title="Batches"
        />

        <Card
          className="lg:col-span-4"
          eyebrow="Source of truth"
          icon={<RadioTower className="h-5 w-5" aria-hidden="true" />}
          title="Ingestion path"
        >
          <div className="space-y-3">
            {["Vendor drops TIFFs into SFTP", "Ingest worker stores raw files", "Classifier worker writes predictions"].map(
              (step, index) => (
                <Card as="div" className="p-4" key={step} variant="subtle">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-sm font-bold text-white dark:bg-white dark:text-ink-950">
                      {index + 1}
                    </div>
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{step}</p>
                  </div>
                </Card>
              ),
            )}
          </div>

          <Card as="div" className="mt-4 p-4" variant="subtle">
            <div className="flex items-start gap-3">
              <ServerCog className="mt-0.5 h-5 w-5 shrink-0 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                No browser upload is provided. This console reflects the SFTP ingestion pipeline.
              </p>
            </div>
          </Card>
        </Card>

        <BatchList batches={batches} className="lg:col-span-8" predictions={predictions} />

        <Card
          className="lg:col-span-12"
          eyebrow="Operational snapshot"
          icon={<FolderInput className="h-5 w-5" aria-hidden="true" />}
          title="Batch states"
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {["pending", "processing", "completed", "failed"].map((state) => (
              <Card as="div" className="p-4" key={state} variant="subtle">
                <p className="text-2xl font-bold text-slate-950 dark:text-white">
                  {batches.filter((batch) => batch.state === state).length}
                </p>
                <p className="mt-1 text-sm font-semibold capitalize text-slate-500 dark:text-slate-400">{state}</p>
              </Card>
            ))}
          </div>
        </Card>
      </motion.div>
    </AppShell>
  );
}
