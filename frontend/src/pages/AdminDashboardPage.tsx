/**
 * Admin Dashboard — /admin
 * Tabs: Issues | Duplicates
 *
 * Issues tab:
 *   - Priority-sorted list with status/category/team filters
 *   - Assign team modal with auto-suggestion
 *
 * Duplicates tab:
 *   - List of child→parent pairs
 *   - Merge (confirm) or Dismiss (unlink) actions
 */
import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, ChevronRight, RefreshCw, Filter, X,
  Users, GitMerge, AlertTriangle, CheckCircle2, Layers,
  TrendingUp, Clock, Copy,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { StatusBadge, PriorityBadge } from "@/components/shared/Badges";
import { ChakraSpinner } from "@/components/shared/ChakraIcon";
import { cn } from "@/lib/utils";

import { BASE_URL as BASE } from "@/api/client";
const token = () => localStorage.getItem("civicfix_token") ?? "";

/* ---------- types ---------- */
interface IssueSummary {
  id: number;
  reference_id: string;
  title: string;
  category: string;
  status: string;
  address: string;
  affected_count: number;
  thumbnail: string | null;
  priority: { score: number; label: string };
  created_at: string;
  suggested_team?: { id: number; name: string } | null;
}

interface Team { id: number; name: string; }

interface DuplicatePair {
  child: IssueSummary;
  parent: IssueSummary | null;
  duplicate_score: number | null;
}

/* ---------- helpers ---------- */
function authFetch(path: string, opts: RequestInit = {}) {
  return fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      Authorization: `Bearer ${token()}`,
      "Content-Type": "application/json",
      ...(opts.headers ?? {}),
    },
  });
}

const CATEGORIES = ["Pothole", "Water Leak", "Garbage", "Streetlight", "Other"];
const STATUSES   = ["Reported", "Assigned", "In Progress", "Resolved", "Reopened"];

/* ======================================================================
   ASSIGN MODAL
   ====================================================================== */
interface AssignModalProps {
  issue: IssueSummary;
  teams: Team[];
  onClose: () => void;
  onDone: () => void;
}

function AssignModal({ issue, teams, onClose, onDone }: AssignModalProps) {
  const [teamId, setTeamId]   = useState<number | "">(issue.suggested_team?.id ?? "");
  const [submitting, setSub]  = useState(false);

  async function submit() {
    if (!teamId) { toast.error("Select a team first."); return; }
    setSub(true);
    try {
      const res  = await authFetch(`/api/admin/issues/${issue.id}/assign`, {
        method: "POST",
        body: JSON.stringify({ team_id: teamId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Assign failed");
      toast.success("Issue assigned & reporter notified!");
      onDone();
    } catch (e: any) {
      toast.error(e.message ?? "Assign failed");
    } finally {
      setSub(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <p className="font-heading font-bold text-navy text-lg">Assign Team</p>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={18} className="text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-gray-600 truncate">
            <span className="font-mono text-xs text-gray-400">{issue.reference_id}</span><br />
            {issue.title}
          </p>

          {issue.suggested_team && (
            <div className="flex items-center gap-2 px-3 py-2 bg-saffron-50 rounded-lg text-sm">
              <TrendingUp size={14} className="text-saffron-dark flex-shrink-0" />
              <span className="text-saffron-dark font-semibold">
                Suggested: {issue.suggested_team.name}
              </span>
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-navy mb-1.5">Team</label>
            <select
              value={teamId}
              onChange={e => setTeamId(Number(e.target.value))}
              className="w-full border border-gray-200 rounded-input px-3 py-2.5 text-sm focus:ring-2 focus:ring-navy/30 focus:border-navy outline-none"
            >
              <option value="">— Select team —</option>
              {teams.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-3 px-6 pb-6">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-input border border-gray-200 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting || !teamId}
            className="flex-1 py-2.5 rounded-input bg-navy text-white text-sm font-semibold hover:bg-navy-900 transition-all disabled:opacity-50"
          >
            {submitting ? "Assigning…" : "Assign & Notify"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ======================================================================
   ISSUE ROW (Admin)
   ====================================================================== */
function AdminIssueRow({
  issue, teams, onUpdate,
}: { issue: IssueSummary; teams: Team[]; onUpdate: () => void }) {
  const [assignModal, setAssign] = useState(false);

  return (
    <>
      <div className="bg-white rounded-card shadow-card border border-gray-100 hover:shadow-md transition-all p-4">
        <div className="flex items-start gap-3">
          {/* Thumbnail */}
          <div className="w-14 h-14 rounded-xl overflow-hidden flex-shrink-0 bg-gray-100">
            {issue.thumbnail
              ? <img src={issue.thumbnail} alt="" className="w-full h-full object-cover" />
              : <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs font-mono">{issue.category[0]}</div>
            }
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 mb-1">
              <StatusBadge status={issue.status as any} />
              <PriorityBadge priority={issue.priority.label as any} />
              <span className="text-gray-400 text-xs font-mono">{issue.reference_id}</span>
              <span className="text-gray-400 text-xs">· {issue.category}</span>
            </div>
            <p className="font-semibold text-navy-900 text-sm leading-snug line-clamp-1">{issue.title}</p>
            <p className="text-gray-400 text-xs mt-0.5 truncate">{issue.address}</p>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-400">
              <span>👥 {issue.affected_count}</span>
              <span>📊 {issue.priority.score.toFixed(1)}</span>
              {issue.suggested_team && (
                <span className="text-saffron-dark font-semibold">
                  💡 {issue.suggested_team.name}
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2 flex-shrink-0">
            <Link
              to={`/issues/${issue.id}`}
              className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-500 hover:text-navy transition-colors"
              title="View"
            >
              <ChevronRight size={16} />
            </Link>
            {["Reported", "Assigned"].includes(issue.status) && (
              <button
                onClick={() => setAssign(true)}
                className="p-2 rounded-lg bg-saffron text-white hover:bg-saffron-dark transition-colors"
                title="Assign team"
              >
                <Users size={16} />
              </button>
            )}
          </div>
        </div>
      </div>

      {assignModal && (
        <AssignModal
          issue={issue}
          teams={teams}
          onClose={() => setAssign(false)}
          onDone={() => { setAssign(false); onUpdate(); }}
        />
      )}
    </>
  );
}

/* ======================================================================
   DUPLICATE ROW
   ====================================================================== */
function DuplicateRow({
  pair, onUpdate,
}: { pair: DuplicatePair; onUpdate: () => void }) {
  const [loading, setLoading] = useState(false);

  async function action(type: "merge" | "dismiss") {
    setLoading(true);
    try {
      const res  = await authFetch(`/api/admin/duplicates/${pair.child.id}/${type}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `${type} failed`);
      toast.success(type === "merge" ? "Duplicate confirmed & counts updated!" : "Link dismissed.");
      onUpdate();
    } catch (e: any) {
      toast.error(e.message ?? `${type} failed`);
    } finally {
      setLoading(false);
    }
  }

  const score = pair.duplicate_score != null ? (pair.duplicate_score * 100).toFixed(0) : "—";

  return (
    <div className="bg-white rounded-card shadow-card border border-gray-100 p-4 space-y-3">
      {/* Score chip */}
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-badge bg-purple-50 text-purple-700 text-xs font-semibold">
          <Copy size={11} /> Similarity {score}%
        </span>
        <div className="flex gap-2">
          <button
            disabled={loading}
            onClick={() => action("merge")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-input bg-navy text-white text-xs font-semibold hover:bg-navy-900 transition-colors disabled:opacity-50"
          >
            <GitMerge size={13} /> Confirm
          </button>
          <button
            disabled={loading}
            onClick={() => action("dismiss")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-input bg-gray-100 text-gray-700 text-xs font-semibold hover:bg-gray-200 transition-colors disabled:opacity-50"
          >
            <X size={13} /> Dismiss
          </button>
        </div>
      </div>

      {/* Child */}
      <div className="rounded-xl bg-gray-50 border border-gray-100 p-3">
        <p className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Duplicate (child)</p>
        <div className="flex items-center gap-2 mb-1">
          <StatusBadge status={pair.child.status as any} />
          <span className="text-xs font-mono text-gray-400">{pair.child.reference_id}</span>
        </div>
        <p className="text-sm font-semibold text-navy-900 line-clamp-1">{pair.child.title}</p>
        <p className="text-xs text-gray-400 mt-0.5 truncate">{pair.child.address}</p>
      </div>

      {/* Parent */}
      {pair.parent && (
        <div className="rounded-xl bg-saffron-50 border border-saffron/20 p-3">
          <p className="text-[10px] text-saffron-dark font-semibold uppercase tracking-wider mb-1.5">Original (parent)</p>
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={pair.parent.status as any} />
            <span className="text-xs font-mono text-gray-400">{pair.parent.reference_id}</span>
          </div>
          <p className="text-sm font-semibold text-navy-900 line-clamp-1">{pair.parent.title}</p>
          <p className="text-xs text-gray-400 mt-0.5 truncate">{pair.parent.address}</p>
          <Link
            to={`/issues/${pair.parent.id}`}
            className="inline-flex items-center gap-1 mt-2 text-xs text-saffron-dark font-semibold hover:underline"
          >
            View original <ChevronRight size={12} />
          </Link>
        </div>
      )}
    </div>
  );
}

/* ======================================================================
   MAIN PAGE
   ====================================================================== */
type PageTab = "issues" | "duplicates";

export function AdminDashboardPage() {
  const { user } = useAuth();

  /* Issues state */
  const [issues, setIssues]     = useState<IssueSummary[]>([]);
  const [teams, setTeams]       = useState<Team[]>([]);
  const [total, setTotal]       = useState(0);
  const [issueLoading, setIL]   = useState(true);
  const [filterStatus, setFS]   = useState("");
  const [filterCat, setFC]      = useState("");
  const [filterTeam, setFT]     = useState<number | "">("");

  /* Duplicates state */
  const [dupes, setDupes]       = useState<DuplicatePair[]>([]);
  const [dupeLoading, setDL]    = useState(false);

  /* Page tab */
  const [tab, setTab]           = useState<PageTab>("issues");
  const [refreshing, setRef]    = useState(false);

  /* ---------- fetch issues ---------- */
  const fetchIssues = useCallback(async () => {
    setRef(true);
    setIL(true);
    try {
      const params = new URLSearchParams({ sort: "priority" });
      if (filterStatus) params.set("status", filterStatus);
      if (filterCat)    params.set("category", filterCat);
      if (filterTeam)   params.set("team_id", String(filterTeam));

      const res  = await authFetch(`/api/admin/issues?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to load issues");
      setIssues(data.items ?? []);
      setTeams(data.teams ?? []);
      setTotal(data.total ?? 0);
    } catch (e: any) {
      toast.error(e.message ?? "Failed to load issues");
    } finally {
      setIL(false);
      setRef(false);
    }
  }, [filterStatus, filterCat, filterTeam]);

  /* ---------- fetch duplicates ---------- */
  const fetchDupes = useCallback(async () => {
    setDL(true);
    try {
      const res  = await authFetch("/api/admin/duplicates");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to load duplicates");
      setDupes(data.items ?? []);
    } catch (e: any) {
      toast.error(e.message ?? "Failed to load duplicates");
    } finally {
      setDL(false);
    }
  }, []);

  useEffect(() => { fetchIssues(); }, [fetchIssues]);
  useEffect(() => { if (tab === "duplicates") fetchDupes(); }, [tab, fetchDupes]);

  /* ---------- counts ---------- */
  const reported   = issues.filter(i => i.status === "Reported").length;
  const inProgress = issues.filter(i => i.status === "In Progress").length;
  const resolved   = issues.filter(i => i.status === "Resolved").length;

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

      {/* ── Header ── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 bg-gradient-to-br from-saffron to-saffron-dark rounded-lg flex items-center justify-center">
              <ShieldCheck size={16} className="text-white" />
            </div>
            <h1 className="font-heading font-bold text-2xl text-navy">Admin Dashboard</h1>
          </div>
          <p className="text-gray-500 text-sm">
            {user?.name} · <span className="font-semibold text-saffron-dark">Administrator</span>
          </p>
        </div>
        <button
          onClick={tab === "issues" ? fetchIssues : fetchDupes}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-2 rounded-input border border-gray-200 bg-white text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* ── Stat cards (issues tab) ── */}
      {tab === "issues" && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { label: "Total", value: total,      icon: Layers,       color: "bg-navy" },
            { label: "Reported", value: reported, icon: AlertTriangle, color: "bg-saffron" },
            { label: "In Progress", value: inProgress, icon: Clock,   color: "bg-amber-400" },
            { label: "Resolved", value: resolved,  icon: CheckCircle2, color: "bg-green" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white rounded-card shadow-card p-4 flex items-center gap-3">
              <div className={`p-2.5 rounded-xl ${color}`}>
                <Icon size={18} className="text-white" />
              </div>
              <div>
                <p className="text-xl font-heading font-bold text-navy-900">{value}</p>
                <p className="text-xs text-gray-500">{label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Page Tabs ── */}
      <div className="flex border-b border-gray-200 mb-5">
        {(["issues", "duplicates"] as PageTab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-5 py-2.5 text-sm font-semibold capitalize border-b-2 -mb-px transition-colors",
              tab === t ? "border-navy text-navy" : "border-transparent text-gray-500 hover:text-navy"
            )}
          >
            {t === "duplicates" ? `Duplicates (${dupes.length})` : `Issues (${total})`}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════
          ISSUES TAB
         ══════════════════════════════════════════ */}
      {tab === "issues" && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-5 items-center">
            <Filter size={15} className="text-gray-400 flex-shrink-0" />

            <select
              value={filterStatus}
              onChange={e => setFS(e.target.value)}
              className="border border-gray-200 rounded-input px-2.5 py-1.5 text-xs font-semibold text-gray-600 focus:ring-1 focus:ring-navy/30 outline-none"
            >
              <option value="">All Statuses</option>
              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            <select
              value={filterCat}
              onChange={e => setFC(e.target.value)}
              className="border border-gray-200 rounded-input px-2.5 py-1.5 text-xs font-semibold text-gray-600 focus:ring-1 focus:ring-navy/30 outline-none"
            >
              <option value="">All Categories</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>

            <select
              value={filterTeam}
              onChange={e => setFT(e.target.value ? Number(e.target.value) : "")}
              className="border border-gray-200 rounded-input px-2.5 py-1.5 text-xs font-semibold text-gray-600 focus:ring-1 focus:ring-navy/30 outline-none"
            >
              <option value="">All Teams</option>
              {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>

            {(filterStatus || filterCat || filterTeam) && (
              <button
                onClick={() => { setFS(""); setFC(""); setFT(""); }}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-500 transition-colors font-semibold"
              >
                <X size={13} /> Clear
              </button>
            )}
          </div>

          {issueLoading ? (
            <ChakraSpinner label="Loading issues…" />
          ) : issues.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <Filter size={40} className="mx-auto mb-2 text-gray-200" />
              <p>No issues match the current filters.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {issues.map(issue => (
                <AdminIssueRow
                  key={issue.id}
                  issue={issue}
                  teams={teams}
                  onUpdate={fetchIssues}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* ══════════════════════════════════════════
          DUPLICATES TAB
         ══════════════════════════════════════════ */}
      {tab === "duplicates" && (
        <>
          {dupeLoading ? (
            <ChakraSpinner label="Loading duplicates…" />
          ) : dupes.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <GitMerge size={40} className="mx-auto mb-2 text-gray-200" />
              <p>No duplicate issues found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {dupes.map(pair => (
                <DuplicateRow
                  key={pair.child.id}
                  pair={pair}
                  onUpdate={fetchDupes}
                />
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
