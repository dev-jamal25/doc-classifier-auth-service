import { BrainCircuit, FileStack, LayoutDashboard, RadioTower } from "lucide-react";

export const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, path: "/dashboard" },
  { label: "Batches", icon: FileStack, path: "/batches" },
  { label: "Review queue", icon: BrainCircuit, path: "/predictions/review" },
  { label: "Demo guide", icon: RadioTower, path: "/demo-ingestion" },
] as const;
