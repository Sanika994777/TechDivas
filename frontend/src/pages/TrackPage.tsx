import { useState } from "react";
import { Search, Clock, MapPin, FileText } from "lucide-react";
import { trackIssue } from "@/api/client";
import type { CivicIssue } from "@/types";
import { StatusBadge, PriorityBadge } from "@/components/shared/Badges";
import { MiniStepper } from "@/components/shared/Timeline";
import { ChatWidget } from "@/components/shared/ChatWidget";
import { Link } from "react-router-dom";

const SLA_DAYS: Record<string, number> = {
  Pothole: 7, "Water Leak": 3, Garbage: 2, Streetlight: 5, Other: 10,
};

function daysAgo(date: string) {
  const diff = Date.now() - new Date(date).getTime();
  return Math.floor(diff / 86400000);
}

export function TrackPage() {
  const [refId, setRefId] = useState("");
  const [issue, setIssue] = useState<CivicIssue | null>(null);
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!refId.trim()) return;
    setLoading(true);
    setNotFound(false);
    setIssue(null);
    const result = await trackIssue(refId.trim());
    if (result) setIssue(result);
    else setNotFound(true);
    setLoading(false);
  }

  const slaTotal = issue ? (SLA_DAYS[issue.category] ?? 10) : 0;
  const elapsed = issue ? Math.min(daysAgo(issue.createdAt), slaTotal) : 0;
  const slaPct = slaTotal ? Math.round((elapsed / slaTotal) * 100) : 0;
  const slaRemaining = Math.max(0, slaTotal - elapsed);
  const isEscalated = slaRemaining === 0 && issue?.status !== "Resolved";

  return (
    <main className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <div className="text-center mb-8">
        <h1 className="font-heading font-bold text-2xl text-navy mb-2">Track Your Complaint</h1>
        <p className="text-gray-500 text-sm">Enter your reference ID to see real-time status updates.</p>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-3 mb-8">
        <div className="relative flex-1">
          <FileText size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            id="ref-id-input"
            type="text"
            placeholder="e.g. CIV-001"
            value={refId}
            onChange={(e) => setRefId(e.target.value.toUpperCase())}
            className="w-full pl-9 pr-4 py-3 border border-gray-200 rounded-input bg-white focus:outline-none focus:ring-2 focus:ring-navy/30 font-mono text-sm tracking-wider"
          />
        </div>
        <button
          type="submit"
          id="track-search-btn"
          disabled={loading}
          className="flex items-center gap-2 bg-navy text-white px-6 py-3 rounded-input font-semibold hover:bg-navy/80 transition-colors disabled:opacity-60"
        >
          <Search size={16} />
          {loading ? "Searching…" : "Track"}
        </button>
      </form>

      {/* Not found */}
      {notFound && (
        <div className="text-center py-10 text-gray-400">
          <p className="text-lg font-heading text-navy-900 mb-1">Complaint not found</p>
          <p className="text-sm">Double-check the reference ID and try again.</p>
          <p className="text-sm mt-2">
            Don't have one?{" "}
            <Link to="/report" className="text-saffron-dark font-semibold hover:underline">
              Report a new issue
            </Link>
          </p>
        </div>
      )}

      {/* Result */}
      {issue && (
        <div className="space-y-5">
          {/* Status card */}
          <div className="bg-white rounded-card shadow-card border border-gray-100 p-6">
            <div className="flex flex-wrap gap-2 mb-3">
              <StatusBadge status={issue.status} />
              <PriorityBadge priority={issue.priority} />
              <span className="text-gray-400 text-xs font-mono">{issue.id}</span>
            </div>
            <h2 className="font-heading font-bold text-xl text-navy-900 mb-1">{issue.title}</h2>
            <div className="flex items-center gap-1.5 text-sm text-gray-500 mb-4">
              <MapPin size={13} className="text-saffron" />
              {issue.address}
            </div>

            {/* Mini stepper */}
            <MiniStepper status={issue.status} />
          </div>

          {/* SLA / ETA card */}
          <div className="bg-white rounded-card shadow-card border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-heading font-semibold text-navy text-sm">SLA Progress</h3>
              {isEscalated ? (
                <span className="text-xs bg-red-100 text-red-600 font-semibold px-2 py-0.5 rounded-badge">
                  ⚠ Escalated
                </span>
              ) : (
                <span className="text-xs text-gray-500">
                  <span className="font-semibold text-navy-900">{slaRemaining}d</span> remaining of {slaTotal}d SLA
                </span>
              )}
            </div>
            <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-700 ${isEscalated ? "bg-red-500" : slaPct > 75 ? "bg-saffron" : "bg-green"}`}
                style={{ width: `${slaPct}%` }}
              />
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4 text-xs">
              <div>
                <p className="text-gray-400 mb-0.5">Assigned Team</p>
                <p className="font-semibold text-navy-900">{issue.team}</p>
              </div>
              <div>
                <p className="text-gray-400 mb-0.5">Expected Resolution</p>
                <div className="flex items-center gap-1 font-semibold text-navy-900">
                  <Clock size={12} className="text-saffron" />
                  {issue.eta}
                </div>
              </div>
              <div>
                <p className="text-gray-400 mb-0.5">Ward</p>
                <p className="font-semibold text-navy-900">{issue.ward}</p>
              </div>
              <div>
                <p className="text-gray-400 mb-0.5">Category</p>
                <p className="font-semibold text-navy-900">{issue.category}</p>
              </div>
            </div>
          </div>

          {/* View full detail link */}
          <div className="text-center">
            <Link
              to={`/issues/${issue.id}`}
              className="inline-flex items-center gap-2 text-sm text-navy font-semibold hover:underline"
            >
              View full complaint details →
            </Link>
          </div>

          {/* Embedded chat assistant */}
          <div>
            <p className="text-xs text-gray-400 mb-2 text-center">Have questions? Ask the CivicFix assistant.</p>
            <ChatWidget embedded issueId={issue.id} />
          </div>
        </div>
      )}
    </main>
  );
}
