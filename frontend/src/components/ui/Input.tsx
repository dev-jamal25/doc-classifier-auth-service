import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/styles";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
};

export function Input({ id, label, hint, className, ...props }: InputProps) {
  const inputId = id ?? props.name;

  return (
    <label className="grid gap-2 text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor={inputId}>
      <span>{label}</span>
      <input
        id={inputId}
        className={cn(
          "h-12 rounded-xl border border-slate-200 bg-white/90 px-4 text-base text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-ocean-500 focus:ring-4 focus:ring-ocean-500/15 dark:border-white/10 dark:bg-white/10 dark:text-white dark:placeholder:text-slate-500",
          className,
        )}
        {...props}
      />
      {hint ? <span className="text-xs font-normal text-slate-500 dark:text-slate-400">{hint}</span> : null}
    </label>
  );
}
