import type { AuditLogEntry, Batch, MockUser, Prediction, TeamUser } from "../types";

export type ListEnvelope<T> = {
  items: T[];
};

export type ApiContracts = {
  me: MockUser;
  batches: ListEnvelope<Batch>;
  predictionsRecent: ListEnvelope<Prediction>;
  auditLog: ListEnvelope<AuditLogEntry>;
  users: ListEnvelope<TeamUser>;
};

export const API_ENDPOINTS = {
  login: "/auth/login",
  me: "/me",
  batches: "/batches",
  recentPredictions: "/predictions/recent",
  auditLog: "/admin/audit-log",
  inviteUser: "/admin/users/invite",
} as const;

export const getConfiguredApiBaseUrl = () => import.meta.env.VITE_API_BASE_URL ?? "";
