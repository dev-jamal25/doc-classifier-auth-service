import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { BrainCircuit, ShieldCheck } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { ReviewQueue } from "../components/predictions/ReviewQueue";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useAuth } from "../lib/auth";
import { REVIEW_THRESHOLD, mockPredictions } from "../lib/mockData";
import { cn } from "../lib/styles";
import type { Role } from "../types";

const roles: Role[] = ["admin", "reviewer", "auditor"];

export function ReviewPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeRole, setActiveRole] = useState<Role>(() => user?.roles[0] ?? "admin");

  if (!user) {
    return null;
  }

  const reviewable = mockPredictions.filter((prediction) => prediction.confidence < REVIEW_THRESHOLD);

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
          action={<Badge tone="amber">{reviewable.length} below threshold</Badge>}
          description="Reviewers work predictions created by the SFTP-to-worker pipeline. This page does not upload TIFFs or bypass ingestion."
          eyebrow="Predictions"
          title="Review queue"
        />

        <Card
          className="lg:col-span-4"
          eyebrow="Permission preview"
          icon={<ShieldCheck className="h-5 w-5" aria-hidden="true" />}
          title="RBAC behavior"
        >
          <div className="grid grid-cols-3 gap-2" role="group" aria-label="Preview review role">
            {roles.map((role) => (
              <button
                className={cn(
                  "rounded-xl px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-500",
                  activeRole === role
                    ? "bg-slate-950 text-white dark:bg-white dark:text-ink-950"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/15",
                )}
                key={role}
                onClick={() => setActiveRole(role)}
                type="button"
              >
                {role}
              </button>
            ))}
          </div>

          <Card as="div" className="mt-4 p-4" variant="subtle">
            <BrainCircuit className="h-5 w-5 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Predictions under 70% confidence are visible to all authenticated roles, but relabel actions are shown
              as reviewer-only.
            </p>
          </Card>
        </Card>

        <ReviewQueue activeRole={activeRole} className="lg:col-span-8" predictions={mockPredictions} />
      </motion.div>
    </AppShell>
  );
}
