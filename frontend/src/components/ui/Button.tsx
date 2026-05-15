import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/styles";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: ReactNode;
};

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-ocean-600 text-white shadow-glow hover:bg-ocean-500 focus-visible:ring-ocean-500",
  secondary:
    "border border-slate-200/80 bg-white/80 text-slate-800 hover:bg-white focus-visible:ring-ocean-500 dark:border-white/10 dark:bg-white/10 dark:text-slate-100 dark:hover:bg-white/15",
  ghost:
    "text-slate-600 hover:bg-slate-100 focus-visible:ring-ocean-500 dark:text-slate-300 dark:hover:bg-white/10",
  danger:
    "bg-rose-600 text-white hover:bg-rose-500 focus-visible:ring-rose-500",
};

export function Button({ className, variant = "primary", icon, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:opacity-60 dark:focus-visible:ring-offset-ink-950",
        variants[variant],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
