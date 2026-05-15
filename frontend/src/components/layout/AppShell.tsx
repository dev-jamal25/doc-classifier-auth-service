import type { ReactNode } from "react";
import type { MockUser, Role } from "../../types";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { MobileNav } from "./MobileNav";

export function AppShell({
  user,
  activeRole,
  onLogout,
  children,
}: {
  user: MockUser;
  activeRole: Role;
  onLogout: () => void;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-ink-950 dark:text-slate-100">
      <div className="fixed inset-0 -z-10 bg-gradient-to-br from-slate-50 via-sky-50 to-emerald-50 dark:from-ink-950 dark:via-slate-950 dark:to-emerald-950/40" />
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar user={user} activeRole={activeRole} onLogout={onLogout} />
          <MobileNav />
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
