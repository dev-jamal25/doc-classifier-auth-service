import { Badge } from "./Badge";
import type { BatchState } from "../../types";

export function StatusBadge({ state }: { state: BatchState }) {
  const tone = {
    pending: "amber",
    processing: "blue",
    completed: "green",
    failed: "rose",
  } as const;

  return <Badge tone={tone[state]}>{state}</Badge>;
}
