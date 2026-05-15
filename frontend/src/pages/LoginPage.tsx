import { Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { BrainCircuit, FileText, ShieldCheck, Sparkles } from "lucide-react";
import { LoginForm } from "../components/auth/LoginForm";
import { useAuth } from "../lib/auth";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="min-h-screen overflow-hidden bg-slate-50 text-slate-950 dark:bg-ink-950 dark:text-white">
      <div className="fixed inset-0 bg-gradient-to-br from-slate-50 via-sky-50 to-emerald-50 dark:from-ink-950 dark:via-slate-950 dark:to-emerald-950/40" />

      <div className="relative mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[1.08fr_0.92fr] lg:px-8">
        <motion.section
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl"
          initial={{ opacity: 0, y: 18 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-2 text-sm font-semibold text-slate-600 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/10 dark:text-slate-200">
            <ShieldCheck className="h-4 w-4 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
            Internal AI review console
          </div>

          <h1 className="max-w-2xl text-4xl font-bold leading-tight text-slate-950 dark:text-white sm:text-6xl">
            Document Classifier Console
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600 dark:text-slate-300">
            Review SFTP batches, inspect classifier confidence, and keep role changes visible through audit history.
          </p>

          <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
            {[
              { label: "SFTP batches", value: "128", icon: FileText },
              { label: "RVL-CDIP labels", value: "16", icon: BrainCircuit },
              { label: "Review threshold", value: "70%", icon: Sparkles },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-2xl border border-slate-200 bg-white/75 p-4 shadow-panel backdrop-blur dark:border-white/10 dark:bg-white/[0.06]"
              >
                <item.icon className="mb-4 h-5 w-5 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
                <p className="text-2xl font-bold text-slate-950 dark:text-white">{item.value}</p>
                <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">{item.label}</p>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-2xl border border-slate-200 bg-white/85 p-6 shadow-panel backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.07] sm:p-8"
          initial={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.45, delay: 0.08, ease: "easeOut" }}
        >
          <div className="mb-8">
            <p className="text-sm font-semibold text-ocean-600 dark:text-sky-300">Secure workspace</p>
            <h2 className="mt-2 text-2xl font-bold text-slate-950 dark:text-white">Sign in</h2>
          </div>

          <LoginForm
            onSubmit={async (email, password) => {
              await login(email, password);
              navigate("/dashboard", { replace: true });
            }}
          />
        </motion.section>
      </div>
    </main>
  );
}
