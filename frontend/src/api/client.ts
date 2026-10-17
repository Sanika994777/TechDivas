/**
 * API client — all calls go through here.
 * When VITE_API_URL is set, requests hit the real FastAPI backend.
 * Without it, mock data is returned with a simulated network delay.
 */

import { MOCK_ISSUES, MOCK_STATS, MOCK_AI_SUGGESTION } from "@/data/mock-issues";
import type { CivicIssue, Stats } from "@/types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

// Simulated delay for mock mode (ms)
const MOCK_DELAY = 600;

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  if (!BASE_URL) {
    // Mock mode — return data without a real HTTP call
    await delay(MOCK_DELAY);
    return {} as T; // callers handle mock branch
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

// ─── Issues ──────────────────────────────────────────────────────────────────

export async function getIssues(): Promise<CivicIssue[]> {
  if (!BASE_URL) { await delay(MOCK_DELAY); return MOCK_ISSUES; }
  return apiFetch<CivicIssue[]>("/api/issues");
}

export async function getIssue(id: string): Promise<CivicIssue | null> {
  if (!BASE_URL) {
    await delay(MOCK_DELAY);
    return MOCK_ISSUES.find((i) => i.id === id) ?? null;
  }
  return apiFetch<CivicIssue>(`/api/issues/${id}`);
}

export async function getMyComplaints(): Promise<CivicIssue[]> {
  if (!BASE_URL) { await delay(MOCK_DELAY); return MOCK_ISSUES.filter((i) => i.mine); }
  return apiFetch<CivicIssue[]>("/api/issues/me");
}

export async function trackComplaint(ref: string): Promise<CivicIssue | null> {
  if (!BASE_URL) {
    await delay(MOCK_DELAY);
    return MOCK_ISSUES.find((i) => i.id.toLowerCase() === ref.trim().toLowerCase()) ?? null;
  }
  return apiFetch<CivicIssue>(`/api/issues/track/${encodeURIComponent(ref)}`);
}

export async function getNearbyIssues(
  _lat: number,
  _lng: number,
  _radiusKm: number
): Promise<CivicIssue[]> {
  if (!BASE_URL) { await delay(MOCK_DELAY); return MOCK_ISSUES; }
  return apiFetch<CivicIssue[]>(`/api/issues/nearby?lat=${_lat}&lng=${_lng}&radius=${_radiusKm}`);
}

// ─── Stats ───────────────────────────────────────────────────────────────────

export async function getStats(): Promise<Stats> {
  if (!BASE_URL) { await delay(MOCK_DELAY); return MOCK_STATS; }
  return apiFetch<Stats>("/api/stats");
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

export async function submitIssue(_payload: ReportPayload): Promise<{ id: string }> {
  if (!BASE_URL) {
    await delay(1200);
    return { id: `CF-2026-0${Math.floor(100000 + Math.random() * 900000)}` };
  }
  const form = new FormData();
  form.append("title", _payload.title);
  form.append("description", _payload.description);
  form.append("category", _payload.category);
  form.append("lat", String(_payload.lat));
  form.append("lng", String(_payload.lng));
  form.append("address", _payload.address);
  _payload.photos.forEach((f) => form.append("photos", f));
  const res = await fetch(`${BASE_URL}/api/issues`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  return res.json();
}

// ─── AI suggestion ────────────────────────────────────────────────────────────

export async function getAiSuggestion(_files: File[]): Promise<typeof MOCK_AI_SUGGESTION> {
  if (!BASE_URL) { await delay(1800); return MOCK_AI_SUGGESTION; }
  return apiFetch<typeof MOCK_AI_SUGGESTION>("/api/ai/suggest", { method: "POST" });
}

// ─── Upvote ───────────────────────────────────────────────────────────────────

export async function upvoteIssue(id: string): Promise<{ affectedCount: number }> {
  if (!BASE_URL) {
    await delay(400);
    const issue = MOCK_ISSUES.find((i) => i.id === id);
    return { affectedCount: (issue?.affectedCount ?? 0) + 1 };
  }
  return apiFetch<{ affectedCount: number }>(`/api/issues/${id}/upvote`, { method: "POST" });
}

// ─── Auth (stubs) ─────────────────────────────────────────────────────────────

export async function login(_email: string, _password: string): Promise<{ token: string }> {
  if (!BASE_URL) { await delay(900); return { token: "mock-jwt-token" }; }
  return apiFetch<{ token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: _email, password: _password }),
  });
}

export async function register(
  _name: string,
  _email: string,
  _password: string
): Promise<{ token: string }> {
  if (!BASE_URL) { await delay(900); return { token: "mock-jwt-token" }; }
  return apiFetch<{ token: string }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ name: _name, email: _email, password: _password }),
  });
}

// ─── Aliases ──────────────────────────────────────────────────────────────────
export const getMyIssues = getMyComplaints;
export const trackIssue  = trackComplaint;
