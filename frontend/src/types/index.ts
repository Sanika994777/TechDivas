// ─── Shared Types ────────────────────────────────────────────────────────────

export type IssueStatus = "Reported" | "Assigned" | "In Progress" | "Resolved" | "Reopened";
export type IssueCategory = "Pothole" | "Water Leak" | "Garbage" | "Streetlight" | "Other";
export type IssuePriority = "Critical" | "High" | "Medium" | "Low";

export interface TimelineEvent {
  status: IssueStatus;
  timestamp: string;       // e.g. "Oct 12, 2026 · 9:41 AM"
  actor: string;           // "Ward Team 14" | "System" | "Citizen"
  note: string;
  photo?: string;          // URL
}

export interface CivicIssue {
  id: string;              // "CF-2026-000123"
  title: string;
  description: string;
  category: IssueCategory;
  status: IssueStatus;
  priority: IssuePriority;
  address: string;
  ward: string;
  lat: number;
  lng: number;
  photos: string[];        // URLs
  beforePhoto?: string;
  afterPhoto?: string;
  affectedCount: number;   // community upvotes
  resolvedCount?: number;
  team: string;
  eta: string;             // "2 days" | "Completed"
  createdAt: string;
  updatedAt: string;
  timeline: TimelineEvent[];
  mine?: boolean;
  distance?: number;       // km from user
  severity: number;        // 1–5
  aiSuggested?: boolean;
}

export interface Stats {
  totalReported: number;
  totalResolved: number;
  avgResolutionDays: number;
}
