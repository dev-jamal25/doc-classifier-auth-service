import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { AuditTimeline } from "../components/dashboard/AuditTimeline";
import { BatchQueue } from "../components/dashboard/BatchQueue";
import { DashboardMetrics } from "../components/dashboard/DashboardMetrics";
import { PredictionReviewPanel } from "../components/dashboard/PredictionReviewPanel";
import { RoleUserSummary } from "../components/dashboard/RoleUserSummary";
import { useAuth } from "../lib/auth";
import {
  API_ENDPOINTS,
  type ApiBatch,
  type ApiAuditLogEntry,
  type ApiPrediction,
  mapBatch,
  mapAuditLogEntry,
  mapPrediction,
} from "../lib/api";
import { apiGet, apiUpload } from "../lib/apiClient";
import { mockAuditLog, mockBatches, mockPredictions, mockUsers } from "../lib/mockData";
import type { AuditLogEntry, Batch, Prediction, Role } from "../types";

type UploadState = "idle" | "uploading" | "success" | "error";

function UploadCard({ onBatchCreated }: { onBatchCreated: (batchId: string) => void }) {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [message, setMessage] = useState("");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  async function handleFile(file: File) {
    if (!file.name.match(/\.(tif|tiff)$/i)) {
      setUploadState("error");
      setMessage("Only .tif / .tiff files are accepted.");
      return;
    }
    setUploadState("uploading");
    setMessage("");
    try {
      const res = await apiUpload(API_ENDPOINTS.demoIngest, file);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Upload failed." }));
        throw new Error((body as { detail?: string }).detail ?? "Upload failed.");
      }
      const data = (await res.json()) as { batch_id: string; state: string };
      setBatchId(data.batch_id);
      setUploadState("success");
      setMessage(`Batch created — classifying now.`);
      onBatchCreated(data.batch_id);
    } catch (err) {
      setUploadState("error");
      setMessage(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }

  const borderColor =
    dragging ? "border-blue-500" :
    uploadState === "success" ? "border-green-500" :
    uploadState === "error" ? "border-red-400" :
    "border-gray-600";

  return (
    <div className="lg:col-span-12">
      <div
        className={`rounded-xl border-2 border-dashed ${borderColor} bg-gray-800/50 p-6 transition-colors`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div className="flex flex-col items-center gap-3 text-center sm:flex-row sm:justify-between sm:text-left">
          <div>
            <p className="text-sm font-medium text-gray-200">
              {uploadState === "uploading" && "Uploading…"}
              {uploadState === "success" && message}
              {uploadState === "error" && message}
              {uploadState === "idle" && "Drop a TIFF here to classify it"}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">
              {uploadState === "idle" && "Accepts .tif / .tiff · max 50 MB"}
              {uploadState === "success" && batchId && (
                <button
                  className="text-blue-400 underline"
                  onClick={() => navigate(`/batches/${batchId}`)}
                >
                  View batch →
                </button>
              )}
            </p>
          </div>

          <div className="flex gap-2">
            {uploadState === "success" && (
              <button
                className="rounded-lg bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
                onClick={() => { setUploadState("idle"); setBatchId(null); setMessage(""); }}
              >
                Upload another
              </button>
            )}
            {(uploadState === "idle" || uploadState === "error") && (
              <button
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
                onClick={() => inputRef.current?.click()}
              >
                Choose file
              </button>
            )}
            {uploadState === "uploading" && (
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            )}
          </div>
        </div>
        <input
          ref={inputRef}
          accept=".tif,.tiff,image/tiff"
          className="hidden"
          type="file"
          onChange={onInputChange}
        />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeRole, setActiveRole] = useState<Role>(() => user?.roles[0] ?? "admin");
  const [batches, setBatches] = useState<Batch[]>(mockBatches);
  const [predictions, setPredictions] = useState<Prediction[]>(mockPredictions);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>(mockAuditLog);

  useEffect(() => {
    if (user?.roles[0]) {
      setActiveRole(user.roles[0]);
    }
  }, [user]);

  function refreshBatches() {
    apiGet<{ items: ApiBatch[] }>(API_ENDPOINTS.batches)
      .then((data) => setBatches(data.items.map(mapBatch)))
      .catch(() => {});
  }

  useEffect(() => {
    refreshBatches();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    apiGet<{ items: ApiPrediction[] }>(API_ENDPOINTS.recentPredictions)
      .then((data) => setPredictions(data.items.map(mapPrediction)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeRole === "admin") {
      apiGet<{ items: ApiAuditLogEntry[] }>(API_ENDPOINTS.auditLog)
        .then((data) => setAuditLog(data.items.map(mapAuditLogEntry)))
        .catch(() => {});
    }
  }, [activeRole]);

  if (!user) {
    return null;
  }

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
          description="Monitor SFTP ingestion, review low-confidence predictions, and keep role-sensitive activity visible for the demo flow."
          eyebrow="Overview"
          title="Dashboard"
        />

        <DashboardMetrics batches={batches} predictions={predictions} auditLog={auditLog} />

        <UploadCard onBatchCreated={() => setTimeout(refreshBatches, 1500)} />

        <PredictionReviewPanel activeRole={activeRole} className="lg:col-span-8" predictions={predictions} />
        <BatchQueue batches={batches} className="lg:col-span-4" />

        <RoleUserSummary activeRole={activeRole} className="lg:col-span-5" onRoleChange={setActiveRole} users={mockUsers} />
        <AuditTimeline className="lg:col-span-7" entries={auditLog} />
      </motion.div>
    </AppShell>
  );
}
