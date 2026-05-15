import { LogOut, Moon, Sun, UserCircle } from "lucide-react";
import { useTheme } from "../../lib/theme";
import type { MockUser, Role } from "../../types";
import { Button } from "../ui/Button";
import { RoleBadge } from "../ui/Badge";

export function TopBar({
  user,
  activeRole,
  onLogout,
}: {
  user: MockUser;
  activeRole: Role;
  onLogout: () => void;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-slate-50/85 px-4 py-3 backdrop-blur-xl dark:border-white/10 dark:bg-ink-950/80 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">Authenticated console</p>
          <h1 className="text-xl font-bold text-slate-950 dark:text-white sm:text-2xl">
            Document classification review
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-3 py-2 dark:border-white/10 dark:bg-white/[0.06] sm:flex">
            <UserCircle className="h-5 w-5 text-slate-500 dark:text-slate-300" aria-hidden="true" />
            <div className="max-w-44 truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
              {user.email}
            </div>
            <RoleBadge role={activeRole} />
          </div>

          <Button
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="h-10 w-10 px-0"
            onClick={toggleTheme}
            type="button"
            variant="secondary"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>

          <Button
            aria-label="Log out"
            className="h-10 w-10 px-0 sm:w-auto sm:px-4"
            icon={<LogOut className="h-4 w-4" aria-hidden="true" />}
            onClick={onLogout}
            type="button"
            variant="ghost"
          >
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
