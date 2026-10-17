import type { IssueStatus, IssuePriority } from "@/types";
import { cn } from "@/lib/utils";

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<IssueStatus, { label: string; bg: string; text: string; dot: string }> = {
  Reported:    { label: "Reported",    bg: "bg-[#FFF4E6]", text: "text-[#E07B00]",  dot: "bg-saffron" },
  Assigned:    { label: "Assigned",    bg: "bg-navy-50",   text: "text-navy",       dot: "bg-navy" },
  "In Progress":{ label: "In Progress", bg: "bg-amber-50",  text: "text-amber-700",  dot: "bg-amber-400" },
  Resolved:    { label: "Resolved",    bg: "bg-green-50",  text: "text-green-dark", dot: "bg-green" },
  Reopened:    { label: "Reopened",    bg: "bg-red-50",    text: "text-red-700",    dot: "bg-red-600" },
};

export function StatusBadge({ status }: { status: IssueStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-badge text-xs font-semibold font-body",
        cfg.bg, cfg.text
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", cfg.dot)} />
      {cfg.label}
    </span>
  );
}

// ─── Priority Badge ───────────────────────────────────────────────────────────

const PRIORITY_CONFIG: Record<IssuePriority, { label: string; bg: string; text: string }> = {
  Critical: { label: "Critical", bg: "bg-red-100",       text: "text-red-700" },
  High:     { label: "High",     bg: "bg-[#FFF4E6]",     text: "text-[#E07B00]" },
  Medium:   { label: "Medium",   bg: "bg-amber-50",      text: "text-amber-700" },
  Low:      { label: "Low",      bg: "bg-green-50",      text: "text-green-dark" },
};

export function PriorityBadge({ priority }: { priority: IssuePriority }) {
  const cfg = PRIORITY_CONFIG[priority];
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-1 rounded-badge text-xs font-semibold font-body",
        cfg.bg, cfg.text
      )}
    >
      {cfg.label}
    </span>
  );
}
