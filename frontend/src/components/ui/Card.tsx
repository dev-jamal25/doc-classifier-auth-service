import type { ElementType, HTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/styles";

type CardVariant = "surface" | "subtle" | "metric" | "interactive";

type CardProps = HTMLAttributes<HTMLElement> & {
  as?: ElementType;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
  eyebrow?: string;
  icon?: ReactNode;
  title?: string;
  action?: ReactNode;
  variant?: CardVariant;
};

const variants: Record<CardVariant, string> = {
  surface:
    "border-slate-200/80 bg-white/85 shadow-panel backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.06]",
  subtle:
    "border-slate-200 bg-slate-50/80 shadow-none dark:border-white/10 dark:bg-white/[0.04]",
  metric:
    "border-slate-200/80 bg-white/85 shadow-panel backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.06]",
  interactive:
    "border-slate-200 bg-slate-50/80 shadow-none transition hover:border-ocean-300 hover:bg-white dark:border-white/10 dark:bg-white/[0.04] dark:hover:border-sky-400/30 dark:hover:bg-white/[0.07]",
};

export function Card({
  as: Component = "section",
  children,
  className,
  contentClassName,
  eyebrow,
  icon,
  title,
  action,
  variant = "surface",
  ...props
}: CardProps) {
  const hasHeader = Boolean(title || eyebrow || icon || action);

  return (
    <Component
      className={cn(
        "min-w-0 rounded-2xl border p-5",
        variant === "metric" ? "flex h-full flex-col justify-between" : "",
        variants[variant],
        className,
      )}
      {...props}
    >
      {hasHeader ? (
        <div className="mb-5 flex min-h-11 items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            {icon ? (
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white dark:bg-white dark:text-ink-950">
                {icon}
              </div>
            ) : null}
            <div className="min-w-0">
              {eyebrow ? (
                <p className="text-xs font-semibold uppercase text-ocean-600 dark:text-sky-300">{eyebrow}</p>
              ) : null}
              {title ? (
                <h2 className="mt-1 truncate text-lg font-semibold text-slate-950 dark:text-white">{title}</h2>
              ) : null}
            </div>
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      ) : null}
      <div className={cn("min-w-0", contentClassName)}>{children}</div>
    </Component>
  );
}
