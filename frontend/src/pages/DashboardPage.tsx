import { useEffect, useState } from "react";
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
import { mockAuditLog, mockBatches, mockPredictions, mockUsers } from "../lib/mockData";
import type { Role } from "../types";

export function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeRole, setActiveRole] = useState<Role>(() => user?.roles[0] ?? "admin");

  useEffect(() => {
    if (user?.roles[0]) {
      setActiveRole(user.roles[0]);
    }
  }, [user]);

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

        <DashboardMetrics batches={mockBatches} predictions={mockPredictions} auditLog={mockAuditLog} />

        <PredictionReviewPanel activeRole={activeRole} className="lg:col-span-8" predictions={mockPredictions} />
        <BatchQueue batches={mockBatches} className="lg:col-span-4" />

        <RoleUserSummary activeRole={activeRole} className="lg:col-span-5" onRoleChange={setActiveRole} users={mockUsers} />
        <AuditTimeline className="lg:col-span-7" entries={mockAuditLog} />
      </motion.div>
    </AppShell>
  );
}
