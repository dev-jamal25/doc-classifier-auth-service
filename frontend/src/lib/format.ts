export const formatPercent = (value: number) => `${Math.round(value * 100)}%`;

export const formatDateTime = (value: string) => {
  if (value === "Invite pending") {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
};

export const labelToTitle = (value: string) =>
  value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
