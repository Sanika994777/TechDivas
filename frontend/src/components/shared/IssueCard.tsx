import { useState } from "react";
import { MapPin, Users, ThumbsUp, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { CivicIssue } from "@/types";
import { StatusBadge, PriorityBadge } from "./Badges";
import { upvoteIssue } from "@/api/client";
import { cn } from "@/lib/utils";

const CATEGORY_ICONS: Record<CivicIssue["category"], string> = {
  "Pothole":    "🕳️",
  "Water Leak": "💧",
  "Garbage":    "🗑️",
  "Streetlight":"💡",
  "Other":      "📋",
};

interface IssueCardProps {
  issue: CivicIssue;
  compact?: boolean;
  className?: string;
}

export function IssueCard({ issue, compact = false, className }: IssueCardProps) {
  const [count, setCount] = useState(issue.affectedCount);
  const [voted, setVoted] = useState(false);
  const [voting, setVoting] = useState(false);

  async function handleUpvote(e: React.MouseEvent) {
    e.preventDefault();
    if (voted || voting) return;
    setVoting(true);
    try {
      const res = await upvoteIssue(issue.id);
      setCount(res.affectedCount);
      setVoted(true);
    } finally {
      setVoting(false);
    }
  }

  return (
    <Link
      to={`/issues/${issue.id}`}
      className={cn(
        "group block bg-white rounded-card shadow-card hover:shadow-card-hover transition-shadow duration-200 overflow-hidden",
        className
      )}
    >
      {/* Photo */}
      {!compact && issue.photos[0] && (
        <div className="relative h-44 overflow-hidden bg-gray-100">
          <img
            src={issue.photos[0]}
            alt={issue.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
          {/* Category chip */}
          <span className="absolute top-2 left-2 bg-white/90 backdrop-blur-sm rounded-badge px-2 py-0.5 text-xs font-semibold text-navy-900">
            {CATEGORY_ICONS[issue.category]} {issue.category}
          </span>
        </div>
      )}

      <div className="p-4">
        {/* Title row */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-heading font-semibold text-navy-900 text-base leading-snug line-clamp-2 group-hover:text-navy transition-colors">
            {issue.title}
          </h3>
          {compact && (
            <span className="text-xl flex-shrink-0">{CATEGORY_ICONS[issue.category]}</span>
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          <StatusBadge status={issue.status} />
          <PriorityBadge priority={issue.priority} />
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 text-xs text-gray-500 font-body mb-3">
          {issue.distance !== undefined && (
            <span className="flex items-center gap-1">
              <MapPin size={12} className="text-saffron" />
              {issue.distance} km
            </span>
          )}
          <span className="flex items-center gap-1">
            <Users size={12} />
            {count} affected
          </span>
          {issue.ward && (
            <span className="truncate hidden sm:block">{issue.ward}</span>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleUpvote}
            disabled={voted || voting}
            className={cn(
              "flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-badge transition-all min-h-[36px]",
              voted
                ? "bg-saffron-50 text-saffron-dark cursor-default"
                : "bg-gray-50 text-gray-600 hover:bg-saffron-50 hover:text-saffron-dark active:scale-95"
            )}
            aria-label="I'm also affected by this issue"
          >
            <ThumbsUp size={12} className={voted ? "fill-saffron text-saffron" : ""} />
            {voted ? "Affected!" : "I'm affected too"}
          </button>

          <span className="flex items-center gap-1 text-xs text-navy font-semibold group-hover:gap-2 transition-all">
            View <ArrowRight size={12} />
          </span>
        </div>
      </div>
    </Link>
  );
}
