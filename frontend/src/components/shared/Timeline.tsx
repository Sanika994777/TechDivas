import type { TimelineEvent } from "@/types";
import { CheckCircle, Circle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_DOT: Record<string, string> = {
  Reported:     "bg-saffron border-saffron",
  Assigned:     "bg-navy border-navy",
  "In Progress":"bg-amber-400 border-amber-400",
  Resolved:     "bg-green border-green",
  Reopened:     "bg-red-600 border-red-600",
};

const STATUS_TEXT: Record<string, string> = {
  Reported:     "text-[#E07B00]",
  Assigned:     "text-navy",
  "In Progress":"text-amber-700",
  Resolved:     "text-green-dark",
  Reopened:     "text-red-700",
};

interface TimelineProps {
  events: TimelineEvent[];
  compact?: boolean;
}

export function Timeline({ events, compact = false }: TimelineProps) {
  return (
    <ol className="relative" aria-label="Issue status timeline">
      {events.map((event, idx) => {
        const isLast = idx === events.length - 1;
        return (
          <li key={idx} className="flex gap-4 pb-6 last:pb-0">
            {/* Dot + line */}
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "w-3 h-3 rounded-full border-2 flex-shrink-0 mt-1",
                  STATUS_DOT[event.status] ?? "bg-gray-300 border-gray-300"
                )}
                aria-hidden="true"
              />
              {!isLast && <span className="w-0.5 flex-1 bg-gray-200 mt-1" />}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-0.5">
                <span className={cn("text-xs font-semibold font-body", STATUS_TEXT[event.status] ?? "text-gray-600")}>
                  {event.status}
                </span>
                <span className="text-[11px] text-gray-400 flex items-center gap-1">
                  <Clock size={10} /> {event.timestamp}
                </span>
              </div>
              <p className="text-xs text-gray-600 font-body mb-1">{event.actor}</p>
              {!compact && (
                <>
                  <p className="text-sm text-navy-900 leading-relaxed">{event.note}</p>
                  {event.photo && (
                    <img
                      src={event.photo}
                      alt="Update photo"
                      className="mt-2 w-32 h-20 object-cover rounded-lg border border-gray-100"
                    />
                  )}
                </>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ─── Mini step stepper (for My Complaints cards) ─────────────────────────────

const STEPS = ["Reported", "Assigned", "In Progress", "Resolved"] as const;

export function MiniStepper({ status }: { status: string }) {
  const currentIdx = STEPS.indexOf(status as typeof STEPS[number]);
  return (
    <div className="flex items-center gap-0 w-full" role="progressbar" aria-label={`Status: ${status}`}>
      {STEPS.map((step, i) => {
        const done = currentIdx > i;
        const active = currentIdx === i;
        return (
          <div key={step} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center",
                  done ? "bg-green" : active ? "bg-saffron" : "bg-gray-200"
                )}
              >
                {done ? (
                  <CheckCircle size={12} className="text-white" />
                ) : active ? (
                  <Circle size={8} className="text-white fill-white" />
                ) : (
                  <Circle size={8} className="text-gray-400" />
                )}
              </span>
              <span className={cn(
                "text-[9px] mt-0.5 text-center leading-tight",
                active ? "text-saffron-dark font-semibold" : done ? "text-green-dark" : "text-gray-400"
              )}>
                {step === "In Progress" ? "In Prog." : step}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <span className={cn("flex-1 h-0.5 mx-0.5", done ? "bg-green" : "bg-gray-200")} />
            )}
          </div>
        );
      })}
    </div>
  );
}
