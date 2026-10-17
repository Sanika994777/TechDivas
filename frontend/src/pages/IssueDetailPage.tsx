import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapPin, Users, ThumbsUp, Check, RefreshCw, Info, ArrowLeft } from "lucide-react";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import { getIssue, upvoteIssue } from "@/api/client";
import type { CivicIssue } from "@/types";
import { StatusBadge, PriorityBadge } from "@/components/shared/Badges";
import { Timeline } from "@/components/shared/Timeline";
import { BeforeAfter } from "@/components/shared/BeforeAfter";
import { ChakraSpinner } from "@/components/shared/ChakraIcon";

// Fix leaflet default icons
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

const SEVERITY_LABELS = ["", "Minor", "Low", "Moderate", "High", "Critical"];

export function IssueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [issue, setIssue] = useState<CivicIssue | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [voted, setVoted] = useState(false);
  const [count, setCount] = useState(0);
  const [galIdx, setGalIdx] = useState(0);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    if (!id) return;
    getIssue(id)
      .then((data) => {
        if (!data) { setNotFound(true); return; }
        setIssue(data);
        setCount(data.affectedCount);
      })
      .finally(() => setLoading(false));
  }, [id]);

  async function handleUpvote() {
    if (!issue || voted) return;
    const res = await upvoteIssue(issue.id);
    setCount(res.affectedCount);
    setVoted(true);
  }

  if (loading) return <div className="py-24"><ChakraSpinner /></div>;
  if (notFound || !issue) return (
    <div className="text-center py-24 px-4">
      <p className="text-2xl font-heading text-navy mb-2">Issue not found</p>
      <p className="text-gray-500 mb-6">The complaint ID may be incorrect.</p>
      <Link to="/track" className="text-saffron-dark font-semibold hover:underline">
        ← Track a complaint
      </Link>
    </div>
  );

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Back */}
      <Link to="/nearby" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-navy mb-6">
        <ArrowLeft size={14} /> Back to Nearby
      </Link>

      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-2 mb-3">
          <StatusBadge status={issue.status} />
          <PriorityBadge priority={issue.priority} />
          <span className="text-xs text-gray-400 font-body flex items-center">{issue.id}</span>
        </div>
        <h1 className="font-heading font-bold text-2xl sm:text-3xl text-navy leading-tight mb-2">
          {issue.title}
        </h1>
        <p className="text-gray-600 text-sm leading-relaxed">{issue.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Left column ── */}
        <div className="lg:col-span-2 space-y-6">
          {/* Photo gallery */}
          {issue.photos.length > 0 && (
            <div>
              <img
                src={issue.photos[galIdx]}
                alt={`Photo ${galIdx + 1} of issue`}
                className="w-full h-72 object-cover rounded-card shadow-card"
              />
              {issue.photos.length > 1 && (
                <div className="flex gap-2 mt-2">
                  {issue.photos.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => setGalIdx(i)}
                      className={`w-16 h-12 rounded-lg overflow-hidden border-2 transition-all ${i === galIdx ? "border-saffron" : "border-transparent"}`}
                    >
                      <img src={p} alt="" className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Priority details */}
          <div className="bg-white rounded-card shadow-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="font-heading font-semibold text-navy">Priority Score</h2>
              <button
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                className="relative text-gray-400 hover:text-navy"
                aria-label="How is priority calculated?"
              >
                <Info size={15} />
                {showTooltip && (
                  <div className="absolute left-6 bottom-0 w-56 bg-navy-900 text-white text-xs rounded-card p-3 z-10 shadow-lg">
                    Priority is calculated from severity, community impact (upvotes), and time unresolved.
                  </div>
                )}
              </button>
            </div>
            <div className="space-y-3">
              {[
                { label: "Severity", value: issue.severity, max: 5 },
                { label: "Community Impact", value: Math.min(5, Math.floor(count / 10)), max: 5 },
                { label: "Time Unresolved", value: 3, max: 5 },
              ].map((bar) => (
                <div key={bar.label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">{bar.label}</span>
                    <span className="font-semibold text-navy-900">
                      {bar.label === "Severity" ? SEVERITY_LABELS[bar.value] : `${bar.value}/${bar.max}`}
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-2 bg-saffron rounded-full transition-all duration-500"
                      style={{ width: `${(bar.value / bar.max) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Before / After (only when resolved) */}
          {issue.status === "Resolved" && issue.beforePhoto && issue.afterPhoto && (
            <div>
              <h2 className="font-heading font-semibold text-navy mb-3">Before & After</h2>
              <BeforeAfter beforeSrc={issue.beforePhoto} afterSrc={issue.afterPhoto} />
            </div>
          )}

          {/* Timeline */}
          <div className="bg-white rounded-card shadow-card p-5">
            <h2 className="font-heading font-semibold text-navy mb-4">Status Timeline</h2>
            <Timeline events={issue.timeline} />
          </div>

          {/* Satisfaction buttons (resolved) */}
          {issue.status === "Resolved" && (
            <div className="bg-green-50 border border-green/20 rounded-card p-5">
              <p className="font-semibold text-navy-900 mb-3">Is the issue fully resolved?</p>
              <div className="flex gap-3">
                <button className="flex-1 flex items-center justify-center gap-2 bg-green text-white font-semibold py-2.5 rounded-badge hover:bg-green-dark transition-colors min-h-[44px]">
                  <Check size={16} /> Satisfied
                </button>
                <button className="flex-1 flex items-center justify-center gap-2 border-2 border-red-500 text-red-600 font-semibold py-2.5 rounded-badge hover:bg-red-50 transition-colors min-h-[44px]">
                  <RefreshCw size={16} /> Reopen
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Right column ── */}
        <div className="space-y-4">
          {/* Meta card */}
          <div className="bg-white rounded-card shadow-card p-5 space-y-4 text-sm">
            <div>
              <p className="text-gray-400 text-xs mb-0.5">Location</p>
              <p className="font-medium text-navy-900 flex items-start gap-1.5">
                <MapPin size={14} className="text-saffron mt-0.5 flex-shrink-0" />
                {issue.address}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-xs mb-0.5">Ward</p>
              <p className="font-medium text-navy-900">{issue.ward}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs mb-0.5">Assigned Team</p>
              <p className="font-medium text-navy-900">{issue.team}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs mb-0.5">ETA</p>
              <p className="font-medium text-navy-900">{issue.eta}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs mb-1">Community Support</p>
              <div className="flex items-center gap-2">
                <Users size={14} className="text-gray-400" />
                <span className="font-semibold text-navy-900">{count} affected</span>
              </div>
              <button
                onClick={handleUpvote}
                disabled={voted}
                className={`mt-2 w-full flex items-center justify-center gap-2 py-2.5 rounded-badge font-semibold text-sm transition-colors min-h-[44px] ${
                  voted ? "bg-saffron-50 text-saffron-dark cursor-default" : "bg-saffron text-navy-900 hover:bg-saffron-dark"
                }`}
              >
                <ThumbsUp size={14} className={voted ? "fill-saffron" : ""} />
                {voted ? "You're counted!" : "I'm affected too"}
              </button>
            </div>
          </div>

          {/* Mini map */}
          <div className="rounded-card overflow-hidden shadow-card border border-gray-100" style={{ height: 200 }}>
            <MapContainer center={[issue.lat, issue.lng]} zoom={15} style={{ height: "100%", width: "100%" }} zoomControl={false} attributionControl={false}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Marker position={[issue.lat, issue.lng]} />
            </MapContainer>
          </div>
        </div>
      </div>
    </main>
  );
}
