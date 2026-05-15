import type { AuditLogEntry, Batch, BatchSource, BatchState, DocumentLabel, Prediction } from "../types";

export type ListEnvelope<T> = {
  items: T[];
};

export const API_ENDPOINTS = {
  login: "/auth/login",
  me: "/me",
  batches: "/batches",
  batchDetail: (id: string) => `/batches/${id}`,
  recentPredictions: "/predictions/recent",
  auditLog: "/admin/audit-log",
  inviteUser: "/admin/users/invite",
  assignRole: (userId: string, role: string) => `/admin/users/${userId}/roles/${role}`,
  removeRole: (userId: string, role: string) => `/admin/users/${userId}/roles/${role}`,
  demoIngest: "/demo/ingest",
} as const;

// Raw API shapes (snake_case from the FastAPI backend)

export type ApiBatch = {
  id: string;
  source_filename: string;
  source: string;
  sftp_user: string | null;
  blob_key: string | null;
  state: string;
  failure_reason: string | null;
  request_id: string;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ApiPrediction = {
  id: string;
  batch_id: string;
  label: string;
  confidence: number;
  top5: Array<[string, number]>;
  overlay_blob_key: string | null;
  model_sha256: string;
  reviewed_by_user_id: string | null;
  reviewed_label: string | null;
  reviewed_at: string | null;
  request_id: string;
  created_at: string;
};

export type ApiAuditLogEntry = {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string;
  target_id: string;
  before_value: Record<string, unknown> | null;
  after_value: Record<string, unknown> | null;
  request_id: string;
  created_at: string;
};

const STATE_PROGRESS: Record<string, number> = {
  pending: 5,
  processing: 50,
  completed: 100,
  failed: 0,
};

export function mapBatch(raw: ApiBatch): Batch {
  return {
    id: raw.id,
    sourceFilename: raw.source_filename,
    source: raw.source as BatchSource,
    sftpUser: raw.sftp_user ?? "unknown",
    state: raw.state as BatchState,
    requestId: raw.request_id,
    failureReason: raw.failure_reason ?? undefined,
    documentCount: 1,
    lowConfidenceCount: 0,
    progress: STATE_PROGRESS[raw.state] ?? 0,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export function mapPrediction(raw: ApiPrediction): Prediction {
  return {
    id: raw.id,
    batchId: raw.batch_id,
    sourceFilename: raw.overlay_blob_key?.split("/").pop() ?? raw.id,
    label: raw.label as DocumentLabel,
    confidence: raw.confidence,
    top5: raw.top5.map(([label, confidence]) => ({
      label: label as DocumentLabel,
      confidence,
    })),
    reviewedLabel: raw.reviewed_label as DocumentLabel | null,
    reviewedByUserId: raw.reviewed_by_user_id,
    createdAt: raw.created_at,
  };
}

export function mapAuditLogEntry(raw: ApiAuditLogEntry): AuditLogEntry {
  const actorEmail = raw.actor_user_id
    ? `User ${raw.actor_user_id.substring(0, 8)}`
    : null;

  return {
    id: raw.id,
    actorEmail,
    action: raw.action as AuditLogEntry["action"],
    targetType: raw.target_type as AuditLogEntry["targetType"],
    targetId: raw.target_id,
    beforeValue: raw.before_value ? JSON.stringify(raw.before_value) : "",
    afterValue: raw.after_value ? JSON.stringify(raw.after_value) : "",
    createdAt: raw.created_at,
  };
}
