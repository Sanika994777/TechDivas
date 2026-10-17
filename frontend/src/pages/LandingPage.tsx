import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, FileText, Search, CheckCircle, AlertCircle } from "lucide-react";
import { getStats, getRecentlyResolved } from "@/api/client";
import type { CivicIssue, Stats } from "@/types";
import { IssueCard } from "@/components/shared/IssueCard";
import { ChakraIcon, ChakraSpinner } from "@/components/shared/ChakraIcon";

// ─── Category tiles ───────────────────────────────────────────────────────────
const CATEGORIES = [
  { icon: "🕳️", label: "Pothole",     desc: "Damaged roads" },
  { icon: "💧", label: "Water Leak",  desc: "Burst pipes, flooding" },
  { icon: "🗑️", label: "Garbage",     desc: "Missed collection" },
  { icon: "💡", label: "Streetlight", desc: "Broken lights" },
  { icon: "📋", label: "Other",       desc: "Drains, encroachment…" },
];

// ─── How-it-works steps ───────────────────────────────────────────────────────
const HOW_STEPS = [
  { n: 1, icon: <FileText size={22} className="text-saffron" />, title: "Report", desc: "Take a photo, describe the issue, drop a pin on the map." },
  { n: 2, icon: <ChakraIcon size={22} color="#000080" />, title: "Assigned", desc: "We route your report to the right Pune ward team automatically." },
  { n: 3, icon: <AlertCircle size={22} className="text-amber-500" />, title: "Fixed", desc: "The team works on it and updates the status in real time." },
  { n: 4, icon: <CheckCircle size={22} className="text-green-DEFAULT" />, title: "You confirm", desc: "Mark it resolved or reopen if the issue persists." },
];

export function LandingPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [resolved, setResolved] = useState<CivicIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStats(), getRecentlyResolved()])
      .then(([s, issues]) => {
        setStats(s);
        setResolved(issues);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <main>
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="bg-white pt-12 pb-16 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-12">
          {/* Text */}
          <div className="flex-1 text-center lg:text-left">
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-saffron-dark bg-saffron-50 px-3 py-1.5 rounded-badge mb-4">
              <ChakraIcon size={16} color="#E07B00" /> Pune Civic Platform
            </span>
            <h1 className="text-4xl sm:text-5xl font-heading font-bold text-navy leading-tight mb-4">
              See a problem?<br />
              <span className="text-saffron">Get it fixed.</span>
            </h1>
            <p className="text-gray-600 text-lg mb-8 max-w-xl mx-auto lg:mx-0">
              Report local civic issues in Pune — potholes, water leaks, broken streetlights — and track them until they're resolved.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center lg:justify-start">
              <Link
                to="/report"
                className="inline-flex items-center justify-center gap-2 bg-saffron text-navy-900 font-heading font-semibold px-6 py-3.5 rounded-badge hover:bg-saffron-dark transition-colors text-base shadow-md min-h-[52px]"
              >
                <FileText size={18} /> Report an Issue
              </Link>
              <Link
                to="/track"
                className="inline-flex items-center justify-center gap-2 border-2 border-green text-green-dark font-heading font-semibold px-6 py-3.5 rounded-badge hover:bg-green-50 transition-colors text-base min-h-[52px]"
              >
                <Search size={18} /> Track a Complaint
              </Link>
            </div>
          </div>

          {/* Hero illustration */}
          <div className="flex-1 max-w-sm lg:max-w-md w-full">
            <CityIllustration />
          </div>
        </div>
      </section>

      {/* ── Category tiles ────────────────────────────────────────────── */}
      <section className="py-12 px-4 sm:px-6 bg-gray-50/60" aria-label="Report by category">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl font-heading text-center text-navy mb-8">What do you want to report?</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {CATEGORIES.map((c) => (
              <Link
                key={c.label}
                to={`/report?category=${encodeURIComponent(c.label)}`}
                className="group flex flex-col items-center gap-2 bg-white rounded-card shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200 p-5 text-center"
              >
                <span className="text-4xl group-hover:scale-110 transition-transform duration-200">{c.icon}</span>
                <span className="font-heading font-semibold text-navy-900 text-sm">{c.label}</span>
                <span className="text-xs text-gray-400 font-body">{c.desc}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Live counters ─────────────────────────────────────────────── */}
      <section className="bg-saffron-50 py-10 px-4 sm:px-6" aria-label="Platform statistics">
        <div className="max-w-7xl mx-auto">
          {loading ? (
            <div className="flex justify-center"><ChakraSpinner label="Loading stats…" /></div>
          ) : stats ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
              <StatCount value={stats.totalReported.toLocaleString("en-IN")} label="Issues Reported" color="text-navy" />
              <StatCount value={stats.totalResolved.toLocaleString("en-IN")} label="Resolved" color="text-green-dark" />
              <StatCount value={`${stats.avgResolutionDays} days`} label="Avg. Resolution Time" color="text-saffron-dark" />
            </div>
          ) : null}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────────────── */}
      <section className="py-16 px-4 sm:px-6 bg-white" aria-label="How CivicFix works">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-heading text-navy text-center mb-12">How it works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {HOW_STEPS.map((step, idx) => (
              <div key={step.n} className="flex flex-col items-center text-center relative">
                {/* Connector */}
                {idx < HOW_STEPS.length - 1 && (
                  <ArrowRight size={20} className="hidden lg:block absolute -right-4 top-8 text-gray-200" />
                )}
                <div className="w-16 h-16 bg-navy-50 rounded-full flex items-center justify-center mb-4 border-2 border-white shadow-card">
                  {step.icon}
                </div>
                <div className="text-xs font-bold text-saffron uppercase tracking-widest mb-1">Step {step.n}</div>
                <h3 className="font-heading font-semibold text-navy text-lg mb-2">{step.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Recently resolved carousel ────────────────────────────────── */}
      <section className="py-16 px-4 sm:px-6 bg-gray-50/60" aria-label="Recently resolved issues">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl sm:text-3xl font-heading text-navy">Recently Resolved</h2>
            <Link to="/nearby?status=Resolved" className="text-sm text-saffron-dark font-semibold hover:underline flex items-center gap-1">
              View all <ArrowRight size={14} />
            </Link>
          </div>
          {loading ? (
            <ChakraSpinner />
          ) : resolved.length === 0 ? (
            <EmptyState message="No resolved issues yet." />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {resolved.slice(0, 3).map((issue) => (
                <IssueCard key={issue.id} issue={issue} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── CTA band ──────────────────────────────────────────────────── */}
      <section className="py-16 px-4 sm:px-6 bg-navy text-white text-center">
        <div className="max-w-2xl mx-auto">
          <ChakraIcon size={48} color="white" className="mx-auto mb-4" />
          <h2 className="text-3xl font-heading font-bold text-white mb-3">
            Your city. Your voice.
          </h2>
          <p className="text-white/70 mb-8 text-lg">
            Every report you file gets the right team on the ground. Join thousands of Pune citizens making a difference.
          </p>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 bg-saffron text-navy-900 font-heading font-bold px-8 py-4 rounded-badge hover:bg-saffron-dark transition-colors text-lg"
          >
            Get Started — It's Free <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </main>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCount({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div>
      <div className={`text-4xl font-heading font-bold ${color} mb-1`}>{value}</div>
      <div className="text-sm text-gray-500 font-body">{label}</div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16 text-gray-400">
      <ChakraIcon size={48} color="#E5E7EB" className="mx-auto mb-3" />
      <p>{message}</p>
    </div>
  );
}

// ─── Simple SVG city illustration ────────────────────────────────────────────

function CityIllustration() {
  return (
    <svg viewBox="0 0 400 280" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full drop-shadow-md" aria-hidden="true">
      {/* Sky */}
      <rect width="400" height="280" fill="#FAFAF7" rx="16"/>
      {/* Sun */}
      <circle cx="340" cy="50" r="30" fill="#FFF4E6" />
      <circle cx="340" cy="50" r="20" fill="#FF9933" opacity="0.6" />
      {/* Buildings */}
      <rect x="20" y="100" width="60" height="140" fill="#EEF0FA" rx="4"/>
      <rect x="30" y="110" width="12" height="12" fill="#000080" opacity="0.2" rx="2"/>
      <rect x="50" y="110" width="12" height="12" fill="#000080" opacity="0.2" rx="2"/>
      <rect x="30" y="130" width="12" height="12" fill="#FF9933" opacity="0.4" rx="2"/>
      <rect x="90" y="70" width="80" height="170" fill="#E8F5E6" rx="4"/>
      <rect x="100" y="80" width="14" height="14" fill="#138808" opacity="0.3" rx="2"/>
      <rect x="120" y="80" width="14" height="14" fill="#138808" opacity="0.3" rx="2"/>
      <rect x="140" y="80" width="14" height="14" fill="#138808" opacity="0.3" rx="2"/>
      <rect x="100" y="102" width="14" height="14" fill="#FF9933" opacity="0.4" rx="2"/>
      <rect x="120" y="102" width="14" height="14" fill="#000080" opacity="0.2" rx="2"/>
      <rect x="180" y="90" width="70" height="150" fill="#FFF4E6" rx="4"/>
      <rect x="190" y="100" width="12" height="12" fill="#FF9933" opacity="0.4" rx="2"/>
      <rect x="210" y="100" width="12" height="12" fill="#FF9933" opacity="0.4" rx="2"/>
      <rect x="260" y="50" width="90" height="190" fill="#EEF0FA" rx="4"/>
      <rect x="272" y="62" width="14" height="14" fill="#000080" opacity="0.3" rx="2"/>
      <rect x="294" y="62" width="14" height="14" fill="#000080" opacity="0.3" rx="2"/>
      <rect x="316" y="62" width="14" height="14" fill="#000080" opacity="0.3" rx="2"/>
      <rect x="272" y="84" width="14" height="14" fill="#FF9933" opacity="0.5" rx="2"/>
      <rect x="294" y="84" width="14" height="14" fill="#138808" opacity="0.4" rx="2"/>
      {/* Road */}
      <rect x="0" y="230" width="400" height="50" fill="#E5E7EB" rx="0"/>
      <rect x="0" y="228" width="400" height="4" fill="#D1D5DB"/>
      {/* Road markings */}
      <rect x="30" y="248" width="40" height="4" fill="white" opacity="0.6" rx="2"/>
      <rect x="100" y="248" width="40" height="4" fill="white" opacity="0.6" rx="2"/>
      <rect x="170" y="248" width="40" height="4" fill="white" opacity="0.6" rx="2"/>
      <rect x="240" y="248" width="40" height="4" fill="white" opacity="0.6" rx="2"/>
      <rect x="310" y="248" width="40" height="4" fill="white" opacity="0.6" rx="2"/>
      {/* Pothole issue pin */}
      <circle cx="130" cy="232" r="12" fill="#FF9933" />
      <text x="130" y="237" textAnchor="middle" fontSize="12">🕳️</text>
      {/* Streetlight */}
      <rect x="358" y="160" width="4" height="70" fill="#9CA3AF" rx="2"/>
      <rect x="348" y="158" width="24" height="8" fill="#9CA3AF" rx="4"/>
      <ellipse cx="360" cy="158" rx="8" ry="4" fill="#FFF4E6" />
    </svg>
  );
}
