import { format, isValid } from "date-fns";

export function safeFormatDate(
  value: Date | undefined | null,
  fmt: string,
  fallback = "—",
): string {
  if (!value || !isValid(value)) return fallback;
  return format(value, fmt);
}

export function parseApiDate(value: unknown): Date | undefined {
  if (!value) return undefined;
  const d = new Date(String(value));
  return isValid(d) ? d : undefined;
}
