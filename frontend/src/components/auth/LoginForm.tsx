import { useState, type FormEvent } from "react";
import { ArrowRight, LockKeyhole, Mail } from "lucide-react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

export function LoginForm({
  onSubmit,
}: {
  onSubmit: (email: string, password: string) => Promise<void>;
}) {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError("Enter an email and password to continue.");
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(email, password);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="grid gap-5" onSubmit={handleSubmit}>
      <Input
        autoComplete="email"
        label="Email"
        name="email"
        onChange={(event) => setEmail(event.target.value)}
        placeholder="name@example.com"
        required
        type="email"
        value={email}
      />

      <Input
        autoComplete="current-password"
        label="Password"
        name="password"
        onChange={(event) => setPassword(event.target.value)}
        placeholder="Enter password"
        required
        type="password"
        value={password}
      />

      {error ? (
        <div
          className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 dark:border-rose-400/20 dark:bg-rose-500/10 dark:text-rose-200"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <Button className="h-12 w-full" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Signing in" : "Sign in"}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>

      <div className="grid grid-cols-2 gap-3 text-sm text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 dark:bg-white/10">
          <Mail className="h-4 w-4 text-ocean-600 dark:text-sky-300" aria-hidden="true" />
          Admin invite
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 dark:bg-white/10">
          <LockKeyhole className="h-4 w-4 text-mint-500" aria-hidden="true" />
          Local session
        </div>
      </div>
    </form>
  );
}
