import { NavLink } from "react-router-dom";
import { cn } from "../../lib/styles";
import { navItems } from "./navigation";

export function MobileNav() {
  return (
    <nav
      aria-label="Mobile navigation"
      className="border-b border-slate-200/70 bg-white/75 px-4 py-3 backdrop-blur-xl dark:border-white/10 dark:bg-ink-950/75 lg:hidden"
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {navItems.map((item) => (
          <NavLink
            className={({ isActive }) =>
              cn(
                "flex min-h-11 items-center justify-center gap-2 rounded-xl px-2 text-center text-xs font-semibold transition",
                isActive
                  ? "bg-slate-950 text-white dark:bg-white dark:text-ink-950"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/15",
              )
            }
            key={item.label}
            to={item.path}
          >
            <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
