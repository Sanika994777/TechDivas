import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, CheckCircle2, Clock, AlertCircle, ChevronRight, FileText } from "lucide-react";
import { getMyIssues, getNotifications, markNotificationRead } from "@/api/client";
import type { Notification } from "@/api/client";
import type { CivicIssue, IssueStatus } from "@/types";
import { StatusBadge, PriorityBadge } from "@/components/shared/Badges";
import { MiniStepper } from "@/components/shared/Timeline";
import { ChakraSpinner } from "@/components/shared/ChakraIcon";
import { cn } from "@/lib/utils";

type Tab = "All" | "Open" | "Resolved";
const TABS: Tab[] = ["All", "Open", "Resolved"];

const OPEN_STATUSES: IssueStatus[] = ["Reported", "Assigned", "In Progress", "Reopened"];

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white rounded-card shadow-card p-5 flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-heading font-bold text-navy-900">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}


export function MyComplaintsPage() {
  const [issues, setIssues] = useState<CivicIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("All");
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifs, setNotifs] = useState<Notification[]>([]);

  useEffect(() => {
    getMyIssues()
      .then(setIssues)
      .finally(() => setLoading(false));
    getNotifications()
      .then(setNotifs)
      .catch(() => {}); // non-fatal if notifications fail
  }, []);

  async function handleMarkAllRead() {
    const unreadIds = notifs.filter((n) => !n.read).map((n) => n.id);
    setNotifs((prev) => prev.map((n) => ({ ...n, read: true })));
    // Fire-and-forget each read call
    unreadIds.forEach((id) => markNotificationRead(id).catch(() => {}));
  }

  const displayed = issues.filter((i) => {
    if (tab === "Open") return OPEN_STATUSES.includes(i.status);
    if (tab === "Resolved") return i.status === "Resolved";
    return true;
  });

  const resolved = issues.filter((i) => i.status === "Resolved").length;
  const open = issues.filter((i) => OPEN_STATUSES.includes(i.status)).length;
  const unread = notifs.filter((n) => !n.read).length;

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading font-bold text-2xl text-navy">My Complaints</h1>
          <p className="text-gray-500 text-sm mt-0.5">Track all issues you've reported</p>
        </div>
        {/* Notifications bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifs((v) => !v)}
            className="relative p-2.5 bg-white border border-gray-200 rounded-card shadow-sm hover:bg-gray-50 transition-colors"
            aria-label="Notifications"
          >
            <Bell size={20} className="text-navy" />
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-saffron rounded-full text-white text-[10px] font-bold flex items-center justify-center">
                {unread}
              </span>
            )}
          </button>

          {showNotifs && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-card shadow-lg border border-gray-100 z-50 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <p className="font-semibold text-navy text-sm">Notifications</p>
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-saffron-dark hover:underline font-semibold"
                >
                  Mark all read
                </button>
              </div>
              {notifs.length === 0 ? (
                <p className="px-4 py-4 text-sm text-gray-400">No notifications yet.</p>
              ) : (
                notifs.map((n) => (
                  <div
                    key={n.id}
                    className={cn("px-4 py-3 border-b border-gray-50 last:border-0 text-sm",
                      !n.read ? "bg-saffron-50" : "bg-white")}
                  >
                    <p className="text-navy-900 leading-snug">{n.text}</p>
                    <p className="text-gray-400 text-xs mt-0.5">{n.time}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Filed" value={issues.length} icon={FileText} color="bg-navy" />
        <StatCard label="Open" value={open} icon={AlertCircle} color="bg-saffron" />
        <StatCard label="In Progress" value={issues.filter((i) => i.status === "In Progress").length} icon={Clock} color="bg-yellow-400" />
        <StatCard label="Resolved" value={resolved} icon={CheckCircle2} color="bg-green" />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-5 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px",
              tab === t
                ? "border-navy text-navy"
                : "border-transparent text-gray-500 hover:text-navy"
            )}
          >
            {t}
            {t !== "All" && (
              <span className={cn("ml-1.5 text-xs rounded-badge px-1.5 py-0.5",
                tab === t ? "bg-navy text-white" : "bg-gray-100 text-gray-500")}>
                {t === "Open" ? open : resolved}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Issue list */}
      {loading ? (
        <ChakraSpinner label="Loading your complaints…" />
      ) : displayed.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <FileText size={40} className="mx-auto mb-2 text-gray-200" />
          <p>No complaints in this category.</p>
          <Link to="/report" className="mt-4 inline-block text-saffron-dark font-semibold hover:underline">
            + Report an issue
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {displayed.map((issue) => (
            <Link
              key={issue.id}
              to={`/issues/${issue.id}`}
              className="group block bg-white rounded-card shadow-card hover:shadow-md border border-gray-100 hover:border-saffron/30 transition-all p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <StatusBadge status={issue.status} />
                    <PriorityBadge priority={issue.priority} />
                    <span className="text-gray-400 text-xs">{issue.id}</span>
                  </div>
                  <p className="font-heading font-semibold text-navy-900 truncate group-hover:text-navy transition-colors">
                    {issue.title}
                  </p>
                  <p className="text-gray-500 text-xs mt-1 truncate">{issue.address}</p>
                  {/* Mini progress stepper */}
                  <div className="mt-3">
                    <MiniStepper status={issue.status} />
                  </div>
                </div>
                <ChevronRight size={18} className="text-gray-300 group-hover:text-saffron flex-shrink-0 mt-1 transition-colors" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
