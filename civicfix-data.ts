export type IssueStatus = "Reported" | "Assigned" | "In Progress" | "Resolved" | "Reopened";
export type IssueCategory = "Pothole" | "Water leak" | "Garbage" | "Streetlight" | "Other";
export type IssuePriority = "Critical" | "High" | "Medium" | "Low";

export interface CivicIssue {
  id: string;
  title: string;
  category: IssueCategory;
  status: IssueStatus;
  priority: IssuePriority;
  address: string;
  ward: string;
  distance: number;
  affected: number;
  updated: string;
  team: string;
  eta: string;
  mine?: boolean;
  left: number;
  top: number;
  note: string;
}

// In production, functions in this module become the single HTTP boundary using VITE_API_URL.
const issues: CivicIssue[] = [
  { id: "CF-2026-000123", title: "Deep pothole near the bus stop", category: "Pothole", status: "In Progress", priority: "High", address: "Karve Road, near Nal Stop, Pune", ward: "Erandwane · Ward 14", distance: 0.4, affected: 28, updated: "Today, 10:24 AM", team: "Road Maintenance · Ward 14", eta: "2 days", mine: true, left: 28, top: 32, note: "Repair crew has marked the area and work is underway." },
  { id: "CF-2026-000118", title: "Water leaking from roadside pipe", category: "Water leak", status: "Assigned", priority: "Medium", address: "Prabhat Road, Deccan Gymkhana", ward: "Deccan · Ward 15", distance: 0.8, affected: 13, updated: "Yesterday, 4:15 PM", team: "Water Supply · Ward 15", eta: "4 days", left: 63, top: 21, note: "The water supply team has accepted the request." },
  { id: "CF-2026-000115", title: "Garbage awaiting collection", category: "Garbage", status: "Resolved", priority: "Low", address: "Lane 5, Kothrud, Pune", ward: "Kothrud · Ward 10", distance: 1.2, affected: 19, updated: "Yesterday, 2:05 PM", team: "Solid Waste · Ward 10", eta: "Completed", mine: true, left: 76, top: 57, note: "The collection team cleared the site and shared an update." },
  { id: "CF-2026-000111", title: "Streetlight out on the footpath", category: "Streetlight", status: "Reported", priority: "Medium", address: "FC Road, Shivajinagar, Pune", ward: "Shivajinagar · Ward 17", distance: 1.7, affected: 8, updated: "2 days ago", team: "Awaiting assignment", eta: "Within 7 days", left: 46, top: 55, note: "Your report is in the ward team's queue." },
  { id: "CF-2026-000108", title: "Uneven road surface by school gate", category: "Pothole", status: "Resolved", priority: "High", address: "Model Colony, Pune", ward: "Gokhalenagar · Ward 18", distance: 2.1, affected: 34, updated: "3 days ago", team: "Road Maintenance · Ward 18", eta: "Completed", mine: true, left: 19, top: 69, note: "The road surface has been levelled and reopened." },
  { id: "CF-2026-000105", title: "Overflowing community bin", category: "Garbage", status: "In Progress", priority: "Low", address: "Aundh Road, Khadki, Pune", ward: "Aundh · Ward 8", distance: 2.4, affected: 16, updated: "3 days ago", team: "Solid Waste · Ward 8", eta: "1 day", left: 52, top: 79, note: "A collection vehicle is scheduled for the area." },
  { id: "CF-2026-000102", title: "Open drain cover near crossing", category: "Other", status: "Reopened", priority: "Critical", address: "JM Road, Pune", ward: "Shivajinagar · Ward 17", distance: 2.8, affected: 42, updated: "4 days ago", team: "Road Safety · Ward 17", eta: "1 day", left: 82, top: 35, note: "The cover shifted again; the request has been reopened." },
  { id: "CF-2026-000099", title: "Water pooling after roadworks", category: "Water leak", status: "Resolved", priority: "Medium", address: "Baner Road, Pune", ward: "Baner · Ward 9", distance: 3.2, affected: 11, updated: "5 days ago", team: "Water Supply · Ward 9", eta: "Completed", left: 37, top: 14, note: "The drain was cleared and the water has receded." },
  { id: "CF-2026-000095", title: "Two streetlights not working", category: "Streetlight", status: "Assigned", priority: "Medium", address: "Paud Road, Kothrud, Pune", ward: "Kothrud · Ward 10", distance: 3.7, affected: 23, updated: "6 days ago", team: "Electrical · Ward 10", eta: "3 days", left: 13, top: 41, note: "An electrician is assigned to check both lights." },
  { id: "CF-2026-000092", title: "Pothole across the left lane", category: "Pothole", status: "Resolved", priority: "High", address: "University Road, Pune", ward: "Aundh · Ward 8", distance: 4.1, affected: 31, updated: "1 week ago", team: "Road Maintenance · Ward 8", eta: "Completed", left: 65, top: 72, note: "The damaged section has been patched." },
  { id: "CF-2026-000088", title: "Construction waste on public path", category: "Other", status: "Reported", priority: "Low", address: "Sinhagad Road, Pune", ward: "Dattawadi · Ward 36", distance: 4.6, affected: 7, updated: "1 week ago", team: "Awaiting assignment", eta: "Within 7 days", left: 31, top: 88, note: "Your report is waiting for review by the ward team." },
  { id: "CF-2026-000083", title: "Missed garbage collection", category: "Garbage", status: "Resolved", priority: "Low", address: "Viman Nagar, Pune", ward: "Viman Nagar · Ward 3", distance: 4.9, affected: 21, updated: "1 week ago", team: "Solid Waste · Ward 3", eta: "Completed", left: 89, top: 75, note: "The lane has been cleared after an extra pickup." },
];

export const categories: IssueCategory[] = ["Pothole", "Water leak", "Garbage", "Streetlight", "Other"];
export const statusSteps: IssueStatus[] = ["Reported", "Assigned", "In Progress", "Resolved"];

export const civicApi = {
  async getIssues(): Promise<CivicIssue[]> { return issues; },
  async getIssue(id: string): Promise<CivicIssue | undefined> { return issues.find((issue) => issue.id === id); },
  async getMyComplaints(): Promise<CivicIssue[]> { return issues.filter((issue) => issue.mine); },
  async trackComplaint(reference: string): Promise<CivicIssue | undefined> {
    return issues.find((issue) => issue.id.toLowerCase() === reference.trim().toLowerCase());
  },
};