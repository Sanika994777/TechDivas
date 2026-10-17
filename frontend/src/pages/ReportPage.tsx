import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Check, ChevronRight, MapPin, Copy, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { PhotoUploader } from "@/components/shared/PhotoUploader";
import { MapPicker } from "@/components/shared/MapPicker";
import { StatusBadge } from "@/components/shared/Badges";
import { ChakraIcon } from "@/components/shared/ChakraIcon";
import { getAiSuggestion, submitIssue, getNearbyIssues } from "@/api/client";
import type { CivicIssue } from "@/types";
import { cn } from "@/lib/utils";

const CATEGORIES: CivicIssue["category"][] = ["Pothole", "Water Leak", "Garbage", "Streetlight", "Other"];
const CAT_ICONS: Record<string, string> = {
  "Pothole":"🕳️","Water Leak":"💧","Garbage":"🗑️","Streetlight":"💡","Other":"📋"
};
const STEPS = ["Photos", "Details", "Location", "Review"];

const PUNE_CENTER = { lat: 18.5204, lng: 73.8567 };

type WizardForm = {
  photos: File[];
  title: string;
  description: string;
  category: CivicIssue["category"] | "";
  lat: number;
  lng: number;
  address: string;
};

type AiSuggestion = {
  category: CivicIssue["category"];
  severity: number;
  description: string;
};

export function ReportPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<WizardForm>({
    photos: [],
    title: "",
    description: "",
    category: (params.get("category") as CivicIssue["category"]) || "",
    lat: PUNE_CENTER.lat,
    lng: PUNE_CENTER.lng,
    address: "Pune, Maharashtra",
  });
  const [ai, setAi] = useState<AiSuggestion | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAccepted, setAiAccepted] = useState(false);
  const [nearby, setNearby] = useState<CivicIssue[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [doneId, setDoneId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Fetch AI suggestion after photos upload
  useEffect(() => {
    if (form.photos.length > 0 && !ai && !aiLoading) {
      setAiLoading(true);
      getAiSuggestion(form.photos, form.title, form.description)
        .then(setAi)
        .finally(() => setAiLoading(false));
    }
  }, [form.photos.length]);

  // Load similar nearby issues for Step 4
  useEffect(() => {
    if (step === 3) {
      getNearbyIssues(form.lat, form.lng, 1)
        .then((all) =>
          setNearby(
            all
              .filter((i) => i.category === form.category && i.status !== "Resolved")
              .slice(0, 3)
          )
        );
    }
  }, [step]);

  function acceptAi() {
    if (!ai) return;
    setForm((f) => ({
      ...f,
      category: ai.category,
      description: f.description || ai.description,
    }));
    setAiAccepted(true);
  }

  function canAdvance() {
    if (step === 0) return form.photos.length > 0;
    if (step === 1) return form.title.trim().length >= 5 && form.category !== "";
    if (step === 2) return form.address.trim().length > 3;
    return true;
  }

  async function submit() {
    setSubmitting(true);
    try {
      const { id } = await submitIssue({
        title: form.title,
        description: form.description,
        category: form.category as CivicIssue["category"],
        lat: form.lat,
        lng: form.lng,
        address: form.address,
        photos: form.photos,
      });
      setDoneId(id);
    } finally {
      setSubmitting(false);
    }
  }

  function copyId() {
    if (doneId) {
      navigator.clipboard.writeText(doneId).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }

  // ── Success screen ────────────────────────────────────────────────────────
  if (doneId) {
    return (
      <main className="min-h-screen bg-white flex flex-col items-center justify-center px-4 py-16">
        <div className="text-center max-w-sm">
          <div className="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check size={40} className="text-green" />
          </div>
          <h1 className="font-heading font-bold text-2xl text-navy mb-2">Issue Submitted!</h1>
          <p className="text-gray-500 mb-6">Your report has been sent to the Pune ward team.</p>
          {/* Reference ID */}
          <div className="bg-saffron-50 border border-saffron/30 rounded-card p-4 mb-6">
            <p className="text-xs text-gray-500 mb-1">Reference ID</p>
            <p className="font-heading font-bold text-2xl text-navy-900">{doneId}</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={copyId}
              className="flex-1 flex items-center justify-center gap-2 border-2 border-gray-200 text-navy-900 font-semibold py-3 rounded-badge hover:bg-gray-50 transition-colors"
            >
              <Copy size={15} /> {copied ? "Copied!" : "Copy ID"}
            </button>
            <button
              onClick={() => navigate(`/issues/${doneId}`)}
              className="flex-1 flex items-center justify-center gap-2 bg-navy text-white font-semibold py-3 rounded-badge hover:bg-navy/90 transition-colors"
            >
              Track <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50/60 py-8 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-heading font-bold text-2xl text-navy mb-1">Report an Issue</h1>
          <p className="text-gray-500 text-sm">Help your ward team address it faster.</p>
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            {STEPS.map((s, i) => (
              <div key={s} className="flex-1 flex flex-col items-center">
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all",
                    i < step ? "bg-green text-white" : i === step ? "bg-saffron text-navy-900" : "bg-gray-200 text-gray-400"
                  )}
                >
                  {i < step ? <Check size={14} /> : i + 1}
                </div>
                <span className={cn("text-[11px] mt-1 font-body", i === step ? "text-saffron-dark font-semibold" : "text-gray-400")}>
                  {s}
                </span>
              </div>
            ))}
          </div>
          <div className="h-2 bg-gray-200 rounded-full">
            <div
              className="h-2 bg-saffron rounded-full transition-all duration-500"
              style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
              role="progressbar"
              aria-valuenow={step + 1}
              aria-valuemax={STEPS.length}
            />
          </div>
        </div>

        {/* Step panels */}
        <div className="bg-white rounded-card shadow-card p-6 sm:p-8">

          {/* ── Step 0: Photos ── */}
          {step === 0 && (
            <div>
              <h2 className="font-heading font-semibold text-xl text-navy mb-4">Add Photos</h2>
              <PhotoUploader files={form.photos} onChange={(f) => setForm((prev) => ({ ...prev, photos: f }))} />

              {/* AI Suggestion */}
              {aiLoading && (
                <div className="mt-6 flex items-center gap-3 bg-navy-50 rounded-card px-4 py-3">
                  <ChakraIcon size={20} color="#000080" spinning />
                  <p className="text-sm text-navy">Analysing your photo with AI…</p>
                </div>
              )}
              {ai && !aiLoading && !aiAccepted && (
                <div className="mt-6 border border-saffron/40 bg-saffron-50 rounded-card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles size={16} className="text-saffron-dark" />
                    <span className="font-semibold text-sm text-saffron-dark">AI Suggestion</span>
                    <span className="ml-auto bg-saffron text-navy-900 text-xs font-bold px-2 py-0.5 rounded-badge">
                      Severity {ai.severity}/5
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-navy-900 mb-1">
                    {CAT_ICONS[ai.category]} {ai.category}
                  </p>
                  <p className="text-xs text-gray-600 mb-4">{ai.description}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={acceptAi}
                      className="flex-1 bg-saffron text-navy-900 font-semibold text-sm py-2 rounded-badge hover:bg-saffron-dark transition-colors"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => setAi(null)}
                      className="flex-1 border border-gray-300 text-gray-600 font-semibold text-sm py-2 rounded-badge hover:bg-gray-50 transition-colors"
                    >
                      Edit manually
                    </button>
                  </div>
                </div>
              )}
              {aiAccepted && (
                <div className="mt-4 flex items-center gap-2 text-green-dark text-sm">
                  <Check size={14} /> AI suggestion applied
                </div>
              )}
            </div>
          )}

          {/* ── Step 1: Details ── */}
          {step === 1 && (
            <div className="space-y-5">
              <h2 className="font-heading font-semibold text-xl text-navy">Issue Details</h2>
              <div>
                <label htmlFor="title" className="block text-sm font-semibold text-navy-900 mb-1.5">Title <span className="text-red-500">*</span></label>
                <input
                  id="title"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Deep pothole on Karve Road"
                  className="w-full border border-gray-200 rounded-input px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-navy/40"
                  maxLength={100}
                />
                <p className="text-xs text-gray-400 mt-1 text-right">{form.title.length}/100</p>
              </div>
              <div>
                <label htmlFor="desc" className="block text-sm font-semibold text-navy-900 mb-1.5">Description</label>
                <textarea
                  id="desc"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Describe the issue — size, danger level, duration…"
                  className="w-full border border-gray-200 rounded-input px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-navy/40 resize-none"
                  rows={4}
                  maxLength={500}
                />
                <p className="text-xs text-gray-400 mt-1 text-right">{form.description.length}/500</p>
              </div>
              <div>
                <label className="block text-sm font-semibold text-navy-900 mb-2">Category <span className="text-red-500">*</span></label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, category: c }))}
                      className={cn(
                        "flex items-center gap-1.5 px-3 py-2 rounded-badge border text-sm font-medium transition-all",
                        form.category === c
                          ? "bg-saffron border-saffron text-navy-900 shadow-sm"
                          : "bg-white border-gray-200 text-gray-600 hover:border-saffron hover:text-saffron-dark"
                      )}
                    >
                      {CAT_ICONS[c]} {c}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Step 2: Location ── */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="font-heading font-semibold text-xl text-navy">Pin the Location</h2>
              <MapPicker
                lat={form.lat}
                lng={form.lng}
                onChange={(lat, lng, address) => setForm((f) => ({ ...f, lat, lng, address: address ?? f.address }))}
              />
              <div>
                <label htmlFor="address" className="block text-sm font-semibold text-navy-900 mb-1.5">Address</label>
                <div className="relative">
                  <MapPin size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-saffron" />
                  <input
                    id="address"
                    value={form.address}
                    onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                    className="w-full border border-gray-200 rounded-input pl-9 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-navy/40"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── Step 3: Review ── */}
          {step === 3 && (
            <div className="space-y-5">
              <h2 className="font-heading font-semibold text-xl text-navy">Review & Submit</h2>
              {/* Summary */}
              <div className="bg-gray-50 rounded-card p-4 space-y-2 text-sm">
                <Row label="Category">{CAT_ICONS[form.category]} {form.category}</Row>
                <Row label="Title">{form.title}</Row>
                <Row label="Location"><span className="text-gray-500 truncate">{form.address}</span></Row>
                <Row label="Photos">{form.photos.length} attached</Row>
              </div>
              {/* Similar nearby issues */}
              {nearby.length > 0 && (
                <div>
                  <h3 className="font-heading font-semibold text-base text-navy mb-3">Similar issues nearby</h3>
                  <div className="space-y-3">
                    {nearby.map((issue) => (
                      <div key={issue.id} className="flex items-center gap-3 bg-gray-50 rounded-card p-3">
                        {issue.photos[0] && (
                          <img src={issue.photos[0]} alt="" className="w-14 h-14 object-cover rounded-lg flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-navy-900 truncate">{issue.title}</p>
                          <p className="text-xs text-gray-400">{issue.distance} km · {issue.affectedCount} affected</p>
                          <StatusBadge status={issue.status} />
                        </div>
                        <button className="text-xs text-saffron-dark font-semibold hover:underline flex-shrink-0">
                          + Affected
                        </button>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    Consider upvoting an existing report instead of filing a duplicate.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="flex gap-3 mt-6">
          {step > 0 && (
            <button
              onClick={() => setStep(step - 1)}
              className="flex-1 border-2 border-gray-200 text-navy-900 font-semibold py-3 rounded-badge hover:bg-gray-50 transition-colors"
            >
              Back
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canAdvance()}
              className="flex-1 bg-saffron text-navy-900 font-semibold py-3 rounded-badge hover:bg-saffron-dark transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
            >
              Continue <ChevronRight size={16} />
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={submitting}
              className="flex-1 bg-navy text-white font-semibold py-3 rounded-badge hover:bg-navy/90 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {submitting ? <Loader2 size={16} className="animate-spin" /> : null}
              Submit Report
            </button>
          )}
        </div>
      </div>
    </main>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-gray-400 w-20 flex-shrink-0">{label}</span>
      <span className="text-navy-900 font-medium">{children}</span>
    </div>
  );
}
