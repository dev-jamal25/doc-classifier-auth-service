import type { ReactNode } from "react";
import { Card } from "../ui/Card";

export function PageHeader({
  title,
  eyebrow,
  description,
  action,
}: {
  title: string;
  eyebrow?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <Card as="header" className="col-span-full">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div className="min-w-0">
          {eyebrow ? <p className="text-xs font-semibold uppercase text-ocean-600 dark:text-sky-300">{eyebrow}</p> : null}
          <h1 className="mt-2 text-2xl font-bold text-slate-950 dark:text-white sm:text-3xl">{title}</h1>
          {description ? (
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</p>
          ) : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </Card>
  );
}
