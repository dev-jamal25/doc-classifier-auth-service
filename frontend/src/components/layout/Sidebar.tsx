import { NavLink } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { cn } from "../../lib/styles";
import { Card } from "../ui/Card";
import { navItems } from "./navigation";

export function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200/70 bg-white/70 px-5 py-6 backdrop-blur-xl dark:border-white/10 dark:bg-ink-950/60 lg:block">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-ocean-600 text-white shadow-glow">
          <ShieldCheck className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">Doc Classifier</p>
          <h1 className="text-lg font-bold text-slate-950 dark:text-white">Console</h1>
        </div>
      </div>

      <nav aria-label="Primary navigation" className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            className={({ isActive }) =>
              cn(
                "flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition",
                isActive
                  ? "bg-slate-950 text-white shadow-panel dark:bg-white dark:text-ink-950"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10",
              )
            }
            to={item.path}
          >
            <item.icon className="h-4 w-4" aria-hidden="true" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Card as="div" className="mt-8 p-4" variant="subtle">
        <p className="text-sm font-semibold text-slate-950 dark:text-white">Worker pipeline</p>
        <div className="mt-4 space-y-3">
          {["SFTP ingest", "RQ inference", "Review queue"].map((label, index) => (
            <div key={label} className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
              <span
                className={cn(
                  "h-2.5 w-2.5 rounded-full",
                  index === 0 ? "bg-mint-500" : index === 1 ? "bg-ocean-500" : "bg-amberline-400",
                )}
              />
              {label}
            </div>
          ))}
        </div>
      </Card>
    </aside>
  );
}
