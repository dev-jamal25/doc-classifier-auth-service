export type Role = "admin" | "reviewer" | "auditor";

export type MockUser = {
  id: string;
  email: string;
  roles: Role[];
};

export type BatchState = "pending" | "processing" | "completed" | "failed";

export type BatchSource = "sftp-ingest";

export type DocumentLabel =
  | "letter"
  | "form"
  | "email"
  | "handwritten"
  | "advertisement"
  | "scientific_report"
  | "scientific_publication"
  | "specification"
  | "file_folder"
  | "news_article"
  | "budget"
  | "invoice"
  | "presentation"
  | "questionnaire"
  | "resume"
  | "memo";

export type Batch = {
  id: string;
  sourceFilename: string;
  source: BatchSource;
  sftpUser: string;
  state: BatchState;
  requestId: string;
  failureReason?: string;
  documentCount: number;
  lowConfidenceCount: number;
  progress: number;
  createdAt: string;
  updatedAt: string;
};

export type Prediction = {
  id: string;
  batchId: string;
  sourceFilename: string;
  label: DocumentLabel;
  confidence: number;
  top5: Array<{ label: DocumentLabel; confidence: number }>;
  reviewedLabel: DocumentLabel | null;
  reviewedByUserId: string | null;
  createdAt: string;
};

export type AuditAction = "role_change" | "relabel" | "batch_state_change";

export type AuditLogEntry = {
  id: string;
  actorEmail: string | null;
  action: AuditAction;
  targetType: "user" | "prediction" | "batch";
  targetId: string;
  beforeValue: string;
  afterValue: string;
  createdAt: string;
};

export type TeamUser = {
  id: string;
  email: string;
  roles: Role[];
  status: "active" | "invited";
  lastSeen: string;
};
