"""
services/priority.py
─────────────────────────────────────────────────────────────────────────────
Priority scoring engine for CivicFix issues.

priority_score (0-100) = 0.40 × severity + 0.35 × community_impact + 0.25 × time_unresolved

Components
----------
severity (0-100)
    Category base weight scaled by (severity_level / 5), plus keyword boosts.

community_impact (0-100)
    Derived from upvote count + number of merged duplicate children.
    Capped at 100. Each unit = 5 points.

time_unresolved (0-100)
    Grows linearly until SLA, then accelerates 50% faster after SLA breach.
    Capped at 100.

Labels
------
Critical ≥ 75 | High ≥ 55 | Medium ≥ 35 | Low otherwise

Public API
----------
calculate_priority(issue) → PriorityOut
recalculate_and_save(issue, db)   — updates issue.priority_score in place and commits
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models import Issue

from app.schemas import PriorityComponents, PriorityOut, PriorityWeights

# ── SLA per category (days) ───────────────────────────────────────────────────

SLA_DAYS: dict[str, int] = {
    "Pothole":     7,
    "Water Leak":  2,
    "Garbage":     3,
    "Streetlight": 5,
    "Other":       5,
}

# ── Category base weights (0–100 scale) ───────────────────────────────────────
# These represent the inherent urgency of the category type.
# The final severity component = (severity_level / 5) × base_weight + keyword_boost.

CATEGORY_BASE: dict[str, float] = {
    "Water Leak":  90.0,   # exposed wire / water — highest danger
    "Streetlight": 75.0,   # safety at night
    "Pothole":     65.0,   # road safety
    "Garbage":     50.0,   # health / nuisance
    "Other":       45.0,
}

# ── Keyword boosts applied to raw severity score ──────────────────────────────
# Each matching keyword adds KEYWORD_BOOST points (applied once per keyword,
# capped so final severity_score never exceeds 100).

KEYWORD_BOOST = 8.0
BOOST_KEYWORDS = {
    "accident", "accidents",
    "school", "schools",
    "hospital", "hospitals",
    "flooding", "flood", "floods",
    "dangerous", "danger",
}


def _severity_score(issue: "Issue") -> float:
    """Compute the severity component (0–100)."""
    cat_name   = issue.category.value
    base       = CATEGORY_BASE.get(cat_name, 45.0)
    raw        = (issue.severity / 5.0) * base

    # Keyword scan across title + description
    text_lower = f"{issue.title} {issue.description}".lower().split()
    matched    = BOOST_KEYWORDS.intersection(text_lower)
    boosted    = raw + len(matched) * KEYWORD_BOOST

    return min(100.0, boosted)


def _community_impact_score(issue: "Issue") -> float:
    """Compute the community-impact component (0–100).

    upvotes are stored in issue.affected_count (incremented by create + upvote).
    duplicate children are issues that have parent_issue_id == this issue's id.
    """
    # Count duplicate children that are already loaded as the `duplicates` relationship
    duplicate_count = len(issue.duplicates) if issue.duplicates is not None else 0
    raw = (issue.affected_count + duplicate_count) * 5.0
    return min(100.0, raw)


def _time_score(issue: "Issue") -> float:
    """Compute the time-unresolved component (0–100).

    Grows at normal rate until SLA, then 50% faster after the SLA date.
    """
    cat_name = issue.category.value
    sla_days = SLA_DAYS.get(cat_name, 5)

    now     = datetime.now(timezone.utc)
    created = (
        issue.created_at.replace(tzinfo=timezone.utc)
        if issue.created_at.tzinfo is None
        else issue.created_at
    )
    days_open = max(0.0, (now - created).total_seconds() / 86400.0)

    if days_open <= sla_days:
        score = (days_open / sla_days) * 100.0
    else:
        # 100% at SLA, then accelerates by 50% of the base rate per extra day
        days_over = days_open - sla_days
        score     = 100.0 + (days_over / sla_days) * 50.0

    return min(100.0, score)


def _label(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


# ── Public API ────────────────────────────────────────────────────────────────

WEIGHTS = PriorityWeights(severity=0.40, community_impact=0.35, time_unresolved=0.25)


def calculate_priority(issue: "Issue") -> PriorityOut:
    """Return a fully populated PriorityOut for the given issue (no DB writes)."""
    sev_s  = _severity_score(issue)
    ci_s   = _community_impact_score(issue)
    time_s = _time_score(issue)

    score  = round(sev_s * 0.40 + ci_s * 0.35 + time_s * 0.25, 1)
    score  = min(100.0, score)

    return PriorityOut(
        score      = score,
        label      = _label(score),
        components = PriorityComponents(
            severity         = round(sev_s,  1),
            community_impact = round(ci_s,   1),
            time_unresolved  = round(time_s, 1),
        ),
        weights = WEIGHTS,
    )


def recalculate_and_save(issue: "Issue", db: "Session") -> PriorityOut:
    """Recalculate priority, persist `priority_score` on the issue row, and commit."""
    result = calculate_priority(issue)
    issue.priority_score = result.score
    db.add(issue)
    db.commit()
    return result
