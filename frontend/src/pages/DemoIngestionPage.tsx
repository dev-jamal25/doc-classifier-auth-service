import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, BrainCircuit, FileStack, RadioTower, ServerCog } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useAuth } from "../lib/auth";

const demoSteps = [
  "Drop TIFF into SFTP.",
  "Ingestion picks it up.",
  "Worker classifies it.",
  "Batch appears in /batches.",
  "Prediction can be reviewed if low confidence.",
];

export function DemoIngestionPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  const activeRole = user.roles[0] ?? "admin";

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
          action={<Badge tone="blue">Guide only</Badge>}
          description="Use this page during the live demo to explain the SFTP ingestion path. It intentionally does not implement browser upload."
          eyebrow="Demo flow"
          title="SFTP ingestion guide"
        />

        <Card
          className="lg:col-span-7"
          eyebrow="Live walkthrough"
          icon={<RadioTower className="h-5 w-5" aria-hidden="true" />}
          title="How documents enter the console"
        >
          <div className="space-y-3">
            {demoSteps.map((step, index) => (
              <Card as="div" className="p-4" key={step} variant="subtle">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-sm font-bold text-white dark:bg-white dark:text-ink-950">
                    {index + 1}
                  </div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{step}</p>
                </div>
              </Card>
            ))}
          </div>
        </Card>

        <Card
          className="lg:col-span-5"
          eyebrow="Example command"
          icon={<ServerCog className="h-5 w-5" aria-hidden="true" />}
          title="SFTP drop"
        >
          <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-sm leading-7 text-slate-100">
            <code>{`sftp -P 2222 <sftp-user>@localhost
sftp> cd upload
sftp> put sample-document.tiff
sftp> bye`}</code>
          </pre>

          <Card as="div" className="mt-4 p-4" variant="subtle">
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              The browser never receives the TIFF. The backend ingestion worker observes SFTP, stores the file, and
              creates the batch/prediction records shown in this mock UI.
            </p>
          </Card>
        </Card>

        <Card
          className="lg:col-span-6"
          eyebrow="After ingestion"
          icon={<FileStack className="h-5 w-5" aria-hidden="true" />}
          title="Open batches"
          action={
            <Link
              className="inline-flex items-center gap-2 text-sm font-semibold text-ocean-700 hover:text-ocean-600 dark:text-sky-300 dark:hover:text-sky-200"
              to="/batches"
            >
              View batches
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          }
        >
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            Use `/batches` to show the scanner-vendor files once the ingestion path has created records.
          </p>
        </Card>

        <Card
          className="lg:col-span-6"
          eyebrow="Low confidence"
          icon={<BrainCircuit className="h-5 w-5" aria-hidden="true" />}
          title="Review predictions"
          action={
            <Link
              className="inline-flex items-center gap-2 text-sm font-semibold text-ocean-700 hover:text-ocean-600 dark:text-sky-300 dark:hover:text-sky-200"
              to="/predictions/review"
            >
              Open review queue
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          }
        >
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            Predictions below the 0.70 confidence threshold are routed to the reviewer flow.
          </p>
        </Card>
      </motion.div>
    </AppShell>
  );
}
