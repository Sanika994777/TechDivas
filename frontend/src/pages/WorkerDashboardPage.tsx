/**
 * Worker Dashboard — /worker
 * Lists all issues for the worker's team.
 * Workers can advance status: Assigned → In Progress → Resolved.
 * Resolved requires a note + an after-photo.
 */
import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2, Clock, AlertCircle, ChevronRight,
  Wrench, Upload, X, Filter, RefreshCw, Camera,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { StatusBadge, PriorityBadge } from "@/components/shared/Badges";
import { ChakraSpinner } from "@/components/shared/ChakraIcon";
import { cn } from "@/lib/utils";

const BASE  = (import.meta as any).env?.VITE_API_URL ?? "";
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
}

type Tab = "All" | "Assigned" | "In Progress" | "Resolved";
const TABS: Tab[] = ["All", "Assigned", "In Progress", "Resolved"];

/* ---------- helpers ---------- */
function authFetch(path: string, opts: RequestInit = {}) {
  return fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      Authorization: `Bearer ${token()}`,
      ...(opts.headers ?? {}),
    },
  });
}

/* ---------- Status Update Modal ---------- */
interface UpdateModalProps {
  issue: IssueSummary;
  onClose: () => void;
  onDone: () => void;
}

function StatusUpdateModal({ issue, onClose, onDone }: UpdateModalProps) {
  const isAssigned   = issue.status === "Assigned" || issue.status === "Reopened";
  const isInProgress = issue.status === "In Progress";
  const nextStatus   = isAssigned ? "In Progress" : isInProgress ? "Resolved" : null;

  const [note, setNote]       = useState("");
  const [photo, setPhoto]     = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [submitting, setSub]  = useState(false);
  const fileRef               = useRef<HTMLInputElement>(null);

  if (!nextStatus) return null;

  function pickFile(f: File) {
    setPhoto(f);
    setPreview(URL.createObjectURL(f));
  }

  async function submit() {
    if (nextStatus === "Resolved" && !note.trim()) {
      toast.error("A resolution note is required."); return;
    }
    if (nextStatus === "Resolved" && !photo) {
      toast.error("An after-photo is required for Resolved status."); return;
    }
    setSub(true);
    try {
      const fd = new FormData();
      fd.append("status", nextStatus as string);
      if (note?.trim()) fd.append("note", note.trim());
      if (photo) fd.append("photo", photo);

      const res = await authFetch(`/api/worker/issues/${issue.id}/status`, {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Update failed");
      toast.success(`Issue moved to ${nextStatus}!`);
      onDone();
    } catch (e: any) {
      toast.error(e.message ?? "Update failed");
    } finally {
      setSub(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <p className="font-heading font-bold text-navy text-lg">Update Status</p>
            <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[280px]">{issue.reference_id} — {issue.title}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={18} className="text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Transition arrow */}
          <div className="flex items-center gap-3">
            <StatusBadge status={issue.status as any} />
            <span className="text-gray-400 text-lg">→</span>
            <StatusBadge status={nextStatus as any} />
          </div>

          {/* Note */}
          <div>
            <label className="block text-sm font-semibold text-navy mb-1.5">
              Note {nextStatus === "Resolved" && <span className="text-red-500">*</span>}
            </label>
            <textarea
              value={note}
              onChange={e => setNote(e.target.value)}
              rows={3}
              placeholder={
                nextStatus === "Resolved"
                  ? "Describe the work completed and confirm the issue is resolved…"
                  : "Optional: describe what's happening on the ground…"
              }
              className="w-full border border-gray-200 rounded-input px-3 py-2.5 text-sm focus:ring-2 focus:ring-navy/30 focus:border-navy resize-none outline-none"
            />
          </div>

          {/* After photo (required for Resolved) */}
          <div>
            <label className="block text-sm font-semibold text-navy mb-1.5">
              After Photo {nextStatus === "Resolved" && <span className="text-red-500">*</span>}
            </label>
            {preview ? (
              <div className="relative rounded-xl overflow-hidden h-36">
                <img src={preview} alt="preview" className="w-full h-full object-cover" />
                <button
                  onClick={() => { setPhoto(null); setPreview(null); }}
                  className="absolute top-2 right-2 bg-black/60 text-white rounded-full p-1 hover:bg-black/80"
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => fileRef.current?.click()}
                className={cn(
                  "w-full border-2 border-dashed rounded-xl h-28 flex flex-col items-center justify-center gap-2 transition-colors",
                  nextStatus === "Resolved"
                    ? "border-red-200 hover:border-red-400 bg-red-50"
                    : "border-gray-200 hover:border-navy/40 bg-gray-50"
                )}
              >
                <Camera size={24} className={nextStatus === "Resolved" ? "text-red-400" : "text-gray-400"} />
                <p className="text-xs text-gray-500">
                  {nextStatus === "Resolved" ? "Required — tap to attach resolved state photo" : "Optional — attach a site photo"}
                </p>
              </button>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={e => e.target.files?.[0] && pickFile(e.target.files[0])}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 pb-6">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-input border border-gray-200 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className={cn(
              "flex-1 py-2.5 rounded-input text-sm font-semibold text-white transition-all",
              nextStatus === "Resolved"
                ? "bg-green hover:bg-green-dark"
                : "bg-navy hover:bg-navy-900",
              submitting && "opacity-60 cursor-not-allowed"
            )}
          >
            {submitting ? "Updating…" : `Mark as ${nextStatus}`}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Stat Card ---------- */
function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number; icon: React.ElementType; color: string;
}) {
  return (
    <div className="bg-white rounded-card shadow-card p-4 flex items-center gap-3">
      <div className={`p-2.5 rounded-xl ${color}`}>
        <Icon size={18} className="text-white" />
      </div>
      <div>
        <p className="text-xl font-heading font-bold text-navy-900">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}

/* ---------- Issue Row ---------- */
function IssueRow({ issue, onUpdate }: { issue: IssueSummary; onUpdate: () => void }) {
  const [modal, setModal] = useState(false);
  const canAdvance = ["Assigned", "In Progress", "Reopened"].includes(issue.status);

  return (
    <>
      <div className="bg-white rounded-card shadow-card border border-gray-100 hover:shadow-md transition-all p-4">
        <div className="flex items-start gap-3">
          {/* Thumbnail */}
          <div className="w-14 h-14 rounded-xl overflow-hidden flex-shrink-0 bg-gray-100">
            {issue.thumbnail
              ? <img src={issue.thumbnail} alt="" className="w-full h-full object-cover" />
              : <div className="w-full h-full flex items-center justify-center"><Wrench size={20} className="text-gray-300" /></div>
            }
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 mb-1">
              <StatusBadge status={issue.status as any} />
              <PriorityBadge priority={issue.priority.label as any} />
              <span className="text-gray-400 text-xs font-mono">{issue.reference_id}</span>
            </div>
            <p className="font-semibold text-navy-900 text-sm leading-snug line-clamp-1">{issue.title}</p>
            <p className="text-gray-400 text-xs mt-0.5 truncate">{issue.address}</p>
            <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
              <span>👥 {issue.affected_count} affected</span>
              <span>📊 Priority: {issue.priority.score}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2 flex-shrink-0">
            <Link
              to={`/issues/${issue.id}`}
              className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-500 hover:text-navy transition-colors"
              title="View detail"
            >
              <ChevronRight size={16} />
            </Link>
            {canAdvance && (
              <button
                onClick={() => setModal(true)}
                className="p-2 rounded-lg bg-navy text-white hover:bg-navy-900 transition-colors"
                title="Update status"
              >
                <Upload size={16} />
              </button>
            )}
            {issue.status === "Resolved" && (
              <span className="p-2 rounded-lg bg-green-50 text-green" title="Resolved">
                <CheckCircle2 size={16} />
              </span>
            )}
          </div>
        </div>
      </div>

      {modal && (
        <StatusUpdateModal
          issue={issue}
          onClose={() => setModal(false)}
          onDone={() => { setModal(false); onUpdate(); }}
        />
      )}
    </>
  );
}

/* ---------- Main Page ---------- */
export function WorkerDashboardPage() {
  const { user } = useAuth();
  const [issues, setIssues]   = useState<IssueSummary[]>([]);
  const [team, setTeam]       = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState<Tab>("All");
  const [refreshing, setRef]  = useState(false);

  async function fetchIssues() {
    setRef(true);
    try {
      const res  = await authFetch("/api/worker/issues");
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setIssues(data.items ?? []);
      setTeam(data.team ?? "");
    } catch (e: any) {
      toast.error(e.message ?? "Failed to load issues");
    } finally {
      setLoading(false);
      setRef(false);
    }
  }

  useEffect(() => { fetchIssues(); }, []);

  const displayed = issues.filter(i => {
    if (tab === "All") return true;
    return i.status === tab;
  });

  const counts = {
    Assigned:    issues.filter(i => i.status === "Assigned" || i.status === "Reopened").length,
    "In Progress": issues.filter(i => i.status === "In Progress").length,
    Resolved:    issues.filter(i => i.status === "Resolved").length,
  };

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 bg-navy rounded-lg flex items-center justify-center">
              <Wrench size={16} className="text-white" />
            </div>
            <h1 className="font-heading font-bold text-2xl text-navy">Worker Dashboard</h1>
          </div>
          <p className="text-gray-500 text-sm">
            {user?.name} · <span className="font-semibold text-saffron-dark">{team || "Loading team…"}</span>
          </p>
        </div>
        <button
          onClick={fetchIssues}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-2 rounded-input border border-gray-200 bg-white text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="To Do" value={counts.Assigned} icon={AlertCircle} color="bg-navy" />
        <StatCard label="In Progress" value={counts["In Progress"]} icon={Clock} color="bg-amber-400" />
        <StatCard label="Resolved" value={counts.Resolved} icon={CheckCircle2} color="bg-green" />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-5 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-2.5 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors",
              tab === t ? "border-navy text-navy" : "border-transparent text-gray-500 hover:text-navy"
            )}
          >
            {t}
            {t !== "All" && (
              <span className={cn(
                "ml-1.5 text-xs rounded-badge px-1.5 py-0.5",
                tab === t ? "bg-navy text-white" : "bg-gray-100 text-gray-500"
              )}>
                {counts[t as keyof typeof counts] ?? 0}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Issue list */}
      {loading ? (
        <ChakraSpinner label="Loading your team's issues…" />
      ) : displayed.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Filter size={40} className="mx-auto mb-2 text-gray-200" />
          <p>No issues in this category.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {displayed.map(issue => (
            <IssueRow key={issue.id} issue={issue} onUpdate={fetchIssues} />
          ))}
        </div>
      )}
    </main>
  );
}
