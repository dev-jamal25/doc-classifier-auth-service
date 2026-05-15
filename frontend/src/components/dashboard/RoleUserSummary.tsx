import { UsersRound } from "lucide-react";
import type { Role, TeamUser } from "../../types";
import { ROLE_DESCRIPTIONS } from "../../lib/mockData";
import { formatDateTime } from "../../lib/format";
import { cn } from "../../lib/styles";
import { Badge, RoleBadge } from "../ui/Badge";
import { Card } from "../ui/Card";

const roles: Role[] = ["admin", "reviewer", "auditor"];

export function RoleUserSummary({
  activeRole,
  onRoleChange,
  users,
  className,
}: {
  activeRole: Role;
  onRoleChange: (role: Role) => void;
  users: TeamUser[];
  className?: string;
}) {
  return (
    <Card
      className={className}
      eyebrow="RBAC"
      icon={<UsersRound className="h-5 w-5" aria-hidden="true" />}
      title="Access overview"
    >
      <Card as="div" className="p-4" variant="subtle">
        <div className="flex items-center gap-2">
          <UsersRound className="h-4 w-4 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
          <p className="text-sm font-bold text-slate-950 dark:text-white">Role preview</p>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2" role="group" aria-label="Preview dashboard role">
          {roles.map((role) => (
            <button
              className={cn(
                "rounded-xl px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-500",
                activeRole === role
                  ? "bg-slate-950 text-white dark:bg-white dark:text-ink-950"
                  : "bg-white text-slate-600 hover:bg-slate-100 dark:bg-white/10 dark:text-slate-300 dark:hover:bg-white/15",
              )}
              key={role}
              onClick={() => onRoleChange(role)}
              type="button"
            >
              {role}
            </button>
          ))}
        </div>

        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{ROLE_DESCRIPTIONS[activeRole]}</p>
      </Card>

      <div className="mt-4 space-y-3">
        {users.map((user) => (
          <Card as="article" className="p-4" key={user.id} variant="subtle">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">{user.email}</h3>
                <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                  Last seen: {formatDateTime(user.lastSeen)}
                </p>
              </div>
              <Badge tone={user.status === "active" ? "green" : "amber"}>{user.status}</Badge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {user.roles.map((role) => (
                <RoleBadge key={role} role={role} />
              ))}
            </div>
          </Card>
        ))}
      </div>
    </Card>
  );
}
