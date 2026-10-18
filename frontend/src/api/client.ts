/**
 * API client — all real calls go through here.
 * VITE_API_URL must be set (e.g. http://localhost:8000).
 *
 * Features:
 *  - JWT attached from localStorage automatically
 *  - 8s timeout with "server waking up" banner + up to 3 retries
 *  - 401 → redirect to /login
 *  - Mapper functions adapt backend snake_case shapes to frontend CivicIssue
 */

import type { CivicIssue, TimelineEvent, Stats, IssueStatus, IssuePriority, IssueCategory } from "@/types";

export const BASE_URL = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? "https://techdivas-civicfix.onrender.com" : "http://localhost:8000")
).replace(/\/$/, "");

// ─── Waking-up banner state ───────────────────────────────────────────────────
let _waking = false;
const _wakingListeners: Array<(w: boolean) => void> = [];

function setWaking(val: boolean) {
  _waking = val;
  _wakingListeners.forEach((fn) => fn(val));
}

export function isWaking() { return _waking; }
export function onWakingChange(fn: (w: boolean) => void) {
  _wakingListeners.push(fn);
  return () => {
    const i = _wakingListeners.indexOf(fn);
    if (i !== -1) _wakingListeners.splice(i, 1);
  };
}

// ─── Token helpers ────────────────────────────────────────────────────────────
function token() { return localStorage.getItem("civicfix_token") ?? ""; }

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const t = token();
  return t ? { Authorization: `Bearer ${t}`, ...extra } : { ...extra };
}

// ─── Core fetch with timeout + retry ─────────────────────────────────────────
const TIMEOUT_MS = 25000;
const MAX_RETRIES = 3;

async function apiFetch<T>(path: string, options: RequestInit = {}, attempt = 1): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...authHeaders({ "Content-Type": "application/json" }),
        ...(options.headers as Record<string, string> ?? {}),
      },
    });
    clearTimeout(timer);
    setWaking(false);

    if (res.status === 401) {
      if (!path.startsWith("/api/auth/")) {
        localStorage.removeItem("civicfix_token");
        localStorage.removeItem("civicfix_user");
        window.location.replace("/login");
      }
      let errorMsg = "Invalid email or password.";
      try {
        const errorData = await res.json();
        if (errorData?.detail) errorMsg = errorData.detail;
      } catch {
        // default message
      }
      throw new Error(errorMsg);
    }
    if (!res.ok) {
      let errorMsg = `API ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData?.detail) errorMsg = errorData.detail;
      } catch {
        const text = await res.text().catch(() => res.statusText);
        if (text) errorMsg = text;
      }
      throw new Error(errorMsg);
    }
    return res.json() as Promise<T>;
  } catch (err: unknown) {
    clearTimeout(timer);
    const isAbort =
      err instanceof Error && (err.name === "AbortError" || err.message.includes("abort"));
    if (isAbort && attempt <= MAX_RETRIES) {
      setWaking(true);
      return apiFetch<T>(path, options, attempt + 1);
    }
    if (attempt > MAX_RETRIES) setWaking(false);
    throw err;
  }
}

/** Multipart fetch — no Content-Type header so browser sets boundary; JWT added. */
async function multipartFetch<T>(path: string, formData: FormData, method = "POST"): Promise<T> {
  const UPLOAD_TIMEOUT_MS = 60_000; // 60s — Cloudinary uploads can be slow
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method,
      body: formData,
      signal: controller.signal,
      headers: authHeaders(), // no Content-Type — browser sets it with boundary
    });
    clearTimeout(timer);
    setWaking(false);
    if (res.status === 401) {
      if (!path.startsWith("/api/auth/")) {
        localStorage.removeItem("civicfix_token");
        localStorage.removeItem("civicfix_user");
        window.location.replace("/login");
      }
      let errorMsg = "Unauthorized";
      try {
        const errorData = await res.json();
        if (errorData?.detail) errorMsg = errorData.detail;
      } catch {
        // default message
      }
      throw new Error(errorMsg);
    }
    if (!res.ok) {
      let errorMsg = `API ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData?.detail) errorMsg = errorData.detail;
      } catch {
        const text = await res.text().catch(() => res.statusText);
        if (text) errorMsg = text;
      }
      throw new Error(errorMsg);
    }
    return res.json() as Promise<T>;
  } catch (err: unknown) {
    clearTimeout(timer);
    throw err;
  }
}

// ─── Mapper functions ─────────────────────────────────────────────────────────

function mapTimeline(t: {
  status: string;
  note: string;
  photo_url?: string;
  actor_role?: string;
  created_at: string;
}): TimelineEvent {
  return {
    status: t.status as IssueStatus,
    timestamp: t.created_at,
    actor: t.actor_role ?? "System",
    note: t.note,
    photo: t.photo_url,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapIssueSummary(s: any): CivicIssue {
  const photos: string[] =
    Array.isArray(s.photos)
      ? s.photos.map((p: { url: string } | string) => (typeof p === "string" ? p : p.url))
      : [];

  const priority: IssuePriority =
    (typeof s.priority === "object" ? s.priority?.label : s.priority) ?? "Medium";

  return {
    _numericId: typeof s.id === "number" ? s.id : parseInt(s.id, 10) || undefined,
    id: s.reference_id ?? String(s.id),
    title: s.title ?? "",
    description: s.description ?? "",
    category: (s.category ?? "Other") as IssueCategory,
    status: (s.status ?? "Reported") as IssueStatus,
    priority: priority as IssuePriority,
    address: s.address ?? "",
    ward: "",
    lat: s.lat ?? 18.5204,
    lng: s.lng ?? 73.8567,
    photos,
    beforePhoto: photos[0],
    afterPhoto: undefined,
    affectedCount: s.affected_count ?? s.affectedCount ?? 0,
    team: typeof s.team === "object" ? (s.team?.name ?? "") : (s.team ?? ""),
    eta: "",
    createdAt: s.created_at ?? s.createdAt ?? new Date().toISOString(),
    updatedAt: s.updated_at ?? s.updatedAt ?? new Date().toISOString(),
    timeline: [],
    mine: s.is_owner ?? s.mine,
    distance: s.distance_m != null ? s.distance_m / 1000 : s.distance,
    severity: s.severity ?? 3,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapIssueDetail(d: any): CivicIssue {
  const allPhotos: Array<{ url: string; kind: string }> = d.photos ?? [];
  const photos = allPhotos.map((p) => p.url);
  const beforePhoto = allPhotos.find((p) => p.kind === "before")?.url;
  const afterPhoto = allPhotos.find((p) => p.kind === "after")?.url;

  const priority: IssuePriority =
    (typeof d.priority === "object" ? d.priority?.label : d.priority) ?? "Medium";

  return {
    _numericId: typeof d.id === "number" ? d.id : parseInt(d.id, 10) || undefined,
    id: d.reference_id ?? String(d.id),
    title: d.title ?? "",
    description: d.description ?? "",
    category: (d.category ?? "Other") as IssueCategory,
    status: (d.status ?? "Reported") as IssueStatus,
    priority: priority as IssuePriority,
    address: d.address ?? "",
    ward: "",
    lat: d.lat ?? 18.5204,
    lng: d.lng ?? 73.8567,
    photos,
    beforePhoto,
    afterPhoto,
    affectedCount: d.affected_count ?? d.affectedCount ?? 0,
    team: typeof d.team === "object" ? (d.team?.name ?? "") : (d.team ?? ""),
    eta: "",
    createdAt: d.created_at ?? d.createdAt ?? new Date().toISOString(),
    updatedAt: d.updated_at ?? d.updatedAt ?? new Date().toISOString(),
    timeline: Array.isArray(d.timeline) ? d.timeline.map(mapTimeline) : [],
    mine: d.is_owner ?? d.mine,
    distance: d.distance_m != null ? d.distance_m / 1000 : d.distance,
    severity: d.severity ?? 3,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapTrackOut(t: any): CivicIssue {
  const daysOpen: number = t.days_open ?? 0;
  const createdAt = new Date(Date.now() - daysOpen * 86_400_000).toISOString();

  const slaInfo: string =
    t.sla_remaining_or_overdue ?? "";

  return {
    id: t.reference_id ?? "",
    title: `${t.category ?? "Issue"} in ${t.area ?? "Pune"}`,
    description: t.last_update?.note ?? "",
    category: (t.category ?? "Other") as IssueCategory,
    status: (t.status ?? "Reported") as IssueStatus,
    priority: (t.priority_label ?? "Medium") as IssuePriority,
    address: t.area ?? "",
    ward: "",
    lat: 18.5204,
    lng: 73.8567,
    photos: [],
    beforePhoto: undefined,
    afterPhoto: t.has_after_photo ? "has_after" : undefined,
    affectedCount: 1,
    team: t.team ?? "",
    eta: slaInfo,
    createdAt,
    updatedAt: t.last_update?.time ?? createdAt,
    timeline: [],
    severity: 3,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapStats(s: any): Stats {
  return {
    totalReported: s.total ?? s.totalReported ?? 0,
    totalResolved: s.resolved ?? s.totalResolved ?? 0,
    avgResolutionDays: s.avg_resolution_days ?? s.avgResolutionDays ?? 0,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapRecentResolved(r: any): CivicIssue {
  return {
    id: r.reference_id ?? "",
    title: r.title ?? "",
    description: "",
    category: (r.category ?? "Other") as IssueCategory,
    status: "Resolved",
    priority: "Low",
    address: r.area ?? "",
    ward: "",
    lat: 18.5204,
    lng: 73.8567,
    photos: [r.before_url, r.after_url].filter(Boolean) as string[],
    beforePhoto: r.before_url,
    afterPhoto: r.after_url,
    affectedCount: 0,
    team: "",
    eta: "Completed",
    createdAt: r.resolved_at ?? new Date().toISOString(),
    updatedAt: r.resolved_at ?? new Date().toISOString(),
    timeline: [],
    severity: 3,
  };
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function login(
  email: string,
  password: string
): Promise<{ token: string; role: string; user: { name: string; email: string } }> {
  const data = await apiFetch<{
    access_token: string;
    token_type: string;
    role: string;
    user: { name: string; email: string; role: string };
  }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return { token: data.access_token, role: data.role, user: data.user };
}

export async function register(
  name: string,
  email: string,
  password: string
): Promise<{ token: string; role: string; user: { name: string; email: string } }> {
  const data = await apiFetch<{
    access_token: string;
    token_type: string;
    role: string;
    user: { name: string; email: string; role: string };
  }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
  return { token: data.access_token, role: data.role, user: data.user };
}

// ─── Issues ───────────────────────────────────────────────────────────────────

/** Fetches issues near the Pune centre (public, for landing + nearby pages). */
export async function getIssues(): Promise<CivicIssue[]> {
  const data = await apiFetch<{ items: unknown[] }>(
    "/api/issues/nearby?lat=18.5204&lng=73.8567&radius=5000"
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.items ?? (data as any) ?? []).map(mapIssueSummary);
}

export async function getRecentlyResolved(): Promise<CivicIssue[]> {
  const data = await apiFetch<unknown[]>("/api/public/recent-resolved?limit=6");
  return (Array.isArray(data) ? data : []).map(mapRecentResolved);
}

export async function getIssue(id: string): Promise<CivicIssue | null> {
  try {
    const data = await apiFetch<unknown>(`/api/issues/${encodeURIComponent(id)}`);
    return mapIssueDetail(data);
  } catch (err: unknown) {
    if (err instanceof Error && err.message.includes("API 404")) return null;
    throw err;
  }
}

export async function getMyComplaints(): Promise<CivicIssue[]> {
  const data = await apiFetch<{ items: unknown[] }>("/api/issues/mine");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.items ?? (data as any) ?? []).map(mapIssueSummary);
}

export async function getNearbyIssues(
  lat: number,
  lng: number,
  radiusKm: number
): Promise<CivicIssue[]> {
  const data = await apiFetch<{ items: unknown[] }>(
    `/api/issues/nearby?lat=${lat}&lng=${lng}&radius=${Math.round(radiusKm * 1000)}`
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.items ?? (data as any) ?? []).map(mapIssueSummary);
}

export async function trackComplaint(ref: string): Promise<CivicIssue | null> {
  try {
    const data = await apiFetch<unknown>(`/api/track/${encodeURIComponent(ref)}`);
    return mapTrackOut(data);
  } catch (err: unknown) {
    if (err instanceof Error && err.message.includes("API 404")) return null;
    throw err;
  }
}

// ─── Stats ───────────────────────────────────────────────────────────────────

export async function getStats(): Promise<Stats> {
  const data = await apiFetch<unknown>("/api/public/stats");
  return mapStats(data);
}

// ─── Submit issue ─────────────────────────────────────────────────────────────

export interface ReportPayload {
  title: string;
  description: string;
  category: CivicIssue["category"];
  lat: number;
  lng: number;
  address: string;
  photos: File[];
}

export async function submitIssue(payload: ReportPayload): Promise<{ id: string }> {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("description", payload.description);
  form.append("category", payload.category);
  form.append("lat", String(payload.lat));
  form.append("lng", String(payload.lng));
  form.append("address", payload.address);
  payload.photos.forEach((f) => form.append("photos", f));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await multipartFetch<any>("/api/issues", form);
  return { id: data.reference_id ?? String(data.id) };
}

// ─── AI suggestion ────────────────────────────────────────────────────────────

export async function getAiSuggestion(
  files: File[],
  title?: string,
  description?: string
): Promise<{ category: CivicIssue["category"]; severity: number; description: string }> {
  const form = new FormData();
  if (files[0]) form.append("photo", files[0]);
  if (title) form.append("title", title);
  if (description) form.append("description", description);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await multipartFetch<any>("/api/issues/analyze-photo", form);
  return {
    category: (data.suggested_category ?? "Other") as CivicIssue["category"],
    severity: data.severity ?? 3,
    description: data.short_description ?? "",
  };
}

// ─── Upvote ───────────────────────────────────────────────────────────────────

export async function upvoteIssue(
  id: string,
  numericId?: number
): Promise<{ affectedCount: number }> {
  const nid = numericId ?? parseInt(id, 10);
  if (!nid || isNaN(nid)) throw new Error("Cannot resolve numeric issue id for upvote");
  const data = await apiFetch<{ affected_count: number; has_upvoted: boolean }>(
    `/api/issues/${nid}/upvote`,
    { method: "POST" }
  );
  return { affectedCount: data.affected_count };
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

export async function submitFeedback(
  numericId: number,
  action: "satisfied" | "reopen"
): Promise<CivicIssue> {
  const data = await apiFetch<unknown>(`/api/issues/${numericId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
  return mapIssueDetail(data);
}

// ─── Notifications ────────────────────────────────────────────────────────────

export interface Notification {
  id: string;
  text: string;
  time: string;
  read: boolean;
}

export async function getNotifications(): Promise<Notification[]> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any[]>("/api/notifications");
  return (Array.isArray(data) ? data : []).map((n) => ({
    id: String(n.id),
    text: n.message ?? n.text ?? "",
    time: n.created_at ?? n.time ?? "",
    read: n.is_read ?? n.read ?? false,
  }));
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiFetch(`/api/notifications/${id}/read`, { method: "POST" });
}

// ─── Bot ─────────────────────────────────────────────────────────────────────

export async function botMessage(
  message: string,
  lang = "en"
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<{ reply: string; status_card?: any; intent?: string; suggestions?: string[] }> {
  return apiFetch("/api/bot/message", {
    method: "POST",
    body: JSON.stringify({ message, lang }),
  });
}

// ─── Aliases ─────────────────────────────────────────────────────────────────
export const getMyIssues = getMyComplaints;
export const trackIssue  = trackComplaint;
