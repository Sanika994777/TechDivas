import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import L from "leaflet";
import { Filter, List, Map as MapIcon, AlertCircle } from "lucide-react";
import { getIssues } from "@/api/client";
import type { CivicIssue, IssueStatus, IssueCategory } from "@/types";
import { IssueCard } from "@/components/shared/IssueCard";
import { StatusBadge } from "@/components/shared/Badges";
import { ChakraSpinner } from "@/components/shared/ChakraIcon";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

// Fix leaflet default icons
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

const STATUS_MARKER_COLOR: Record<IssueStatus, string> = {
  Reported: "#FF9933",
  Assigned: "#000080",
  "In Progress": "#F5B301",
  Resolved: "#138808",
  Reopened: "#C62828",
};

function statusIcon(status: IssueStatus) {
  const color = STATUS_MARKER_COLOR[status];
  return new L.Icon({
    iconUrl: `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="20" height="30"><path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24s12-15 12-24C24 5.373 18.627 0 12 0z" fill="${color}"/><circle cx="12" cy="12" r="5" fill="white"/></svg>`)}`,
    iconSize: [20, 30],
    iconAnchor: [10, 30],
    popupAnchor: [0, -30],
  });
}

const RADII = [0.5, 1, 5] as const;
const CATEGORIES: IssueCategory[] = ["Pothole", "Water Leak", "Garbage", "Streetlight", "Other"];
const STATUSES: IssueStatus[] = ["Reported", "Assigned", "In Progress", "Resolved", "Reopened"];
const PUNE_CENTER: [number, number] = [18.5204, 73.8567];

export function NearbyPage() {
  const [issues, setIssues] = useState<CivicIssue[]>([]);
  const [filtered, setFiltered] = useState<CivicIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"map" | "list">("map");
  const [radius, setRadius] = useState<0.5 | 1 | 5>(5);
  const [catFilter, setCatFilter] = useState<IssueCategory | "">("");
  const [statusFilter, setStatusFilter] = useState<IssueStatus | "">("");
  const [selected, setSelected] = useState<CivicIssue | null>(null);

  useEffect(() => {
    getIssues()
      .then((data) => {
        setIssues(data);
        setFiltered(data);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let out = issues;
    if (catFilter) out = out.filter((i) => i.category === catFilter);
    if (statusFilter) out = out.filter((i) => i.status === statusFilter);
    if (radius < 5) out = out.filter((i) => (i.distance ?? 99) <= radius);
    setFiltered(out);
  }, [issues, catFilter, statusFilter, radius]);

  return (
    <main className="min-h-screen bg-gray-50/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-heading font-bold text-2xl text-navy">Nearby Issues</h1>
            <p className="text-gray-500 text-sm mt-1">{filtered.length} issues around Pune</p>
          </div>
          {/* Mobile view toggle */}
          <div className="flex bg-white rounded-badge border border-gray-200 p-1 md:hidden">
            <button
              onClick={() => setView("map")}
              className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-badge text-sm font-semibold transition-colors",
                view === "map" ? "bg-navy text-white" : "text-gray-500")}
            >
              <MapIcon size={14} /> Map
            </button>
            <button
              onClick={() => setView("list")}
              className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-badge text-sm font-semibold transition-colors",
                view === "list" ? "bg-navy text-white" : "text-gray-500")}
            >
              <List size={14} /> List
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-5">
          {/* Radius */}
          <div className="flex items-center gap-1 bg-white rounded-badge border border-gray-200 p-1">
            {RADII.map((r) => (
              <button
                key={r}
                onClick={() => setRadius(r)}
                className={cn("px-2.5 py-1 rounded-badge text-xs font-semibold transition-colors",
                  radius === r ? "bg-saffron text-navy-900" : "text-gray-500 hover:bg-gray-50")}
              >
                {r < 1 ? `${r * 1000}m` : `${r}km`}
              </button>
            ))}
          </div>
          {/* Category filter */}
          <select
            value={catFilter}
            onChange={(e) => setCatFilter(e.target.value as IssueCategory | "")}
            className="border border-gray-200 rounded-badge px-3 py-1.5 text-xs font-semibold bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-navy/30"
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as IssueStatus | "")}
            className="border border-gray-200 rounded-badge px-3 py-1.5 text-xs font-semibold bg-white text-gray-600 focus:outline-none focus:ring-2 focus:ring-navy/30"
            aria-label="Filter by status"
          >
            <option value="">All Statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {(catFilter || statusFilter) && (
            <button
              onClick={() => { setCatFilter(""); setStatusFilter(""); }}
              className="text-xs text-red-500 font-semibold hover:underline flex items-center gap-1"
            >
              <Filter size={12} /> Clear
            </button>
          )}
        </div>

        {loading ? (
          <ChakraSpinner label="Loading nearby issues…" />
        ) : (
          <div className="flex gap-6 h-[calc(100vh-260px)] min-h-[500px]">
            {/* Map */}
            <div className={cn("flex-1 rounded-card overflow-hidden shadow-card border border-gray-200",
              view === "list" ? "hidden md:block" : "block")}>
              <MapContainer center={PUNE_CENTER} zoom={13} style={{ height: "100%", width: "100%" }}>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Circle
                  center={PUNE_CENTER}
                  radius={radius * 1000}
                  pathOptions={{ color: "#FF9933", fillColor: "#FF9933", fillOpacity: 0.05, dashArray: "6" }}
                />
                {filtered.map((issue) => (
                  <Marker
                    key={issue.id}
                    position={[issue.lat, issue.lng]}
                    icon={statusIcon(issue.status)}
                    eventHandlers={{ click: () => setSelected(issue) }}
                  >
                    <Popup>
                      <div className="text-xs max-w-[180px]">
                        <p className="font-semibold text-navy-900 mb-1">{issue.title}</p>
                        <StatusBadge status={issue.status} />
                        <p className="text-gray-400 mt-1">{issue.address}</p>
                        <Link to={`/issues/${issue.id}`} className="text-navy font-semibold mt-1 block hover:underline">
                          View details →
                        </Link>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>

            {/* List */}
            <div className={cn("w-full md:w-80 lg:w-96 flex-shrink-0 overflow-y-auto space-y-4 pr-1",
              view === "map" ? "hidden md:block" : "block")}>
              {filtered.length === 0 ? (
                <div className="text-center py-16 text-gray-400">
                  <AlertCircle size={40} className="mx-auto mb-2 text-gray-200" />
                  <p>No issues match your filters.</p>
                </div>
              ) : (
                filtered.map((issue) => (
                  <IssueCard
                    key={issue.id}
                    issue={issue}
                    className={cn(selected?.id === issue.id ? "ring-2 ring-saffron" : "")}
                  />
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
