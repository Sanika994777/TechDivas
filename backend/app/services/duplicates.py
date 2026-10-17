"""
services/duplicates.py
─────────────────────────────────────────────────────────────────────────────
Duplicate detection engine for CivicFix issues.

Public API
----------
haversine(lat1, lng1, lat2, lng2) → float
    Returns distance in metres between two geographic coordinates.

duplicate_score(new, existing) → float
    0.5 × distance_score + 0.2 × same_category + 0.3 × text_similarity
    Only meaningful when both issues are open and within 200 m.

find_duplicates(new_issue, db) → list[tuple[Issue, float]]
    Returns open issues of the same category within 200 m, sorted by score desc.

check_and_link_duplicate(new_issue, db) → None
    If best score ≥ 0.65:
      - Sets new_issue.parent_issue_id and new_issue.duplicate_score
      - Increments parent.affected_count
      - Creates a Notification for the reporter

get_similar_candidates(lat, lng, category, text, db) → list[dict]
    Top-5 open candidates near (lat,lng) with distance, status, thumbnail.
    Used by GET /api/issues/similar (pre-submit panel).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models import Issue

from app.models import Issue, Notification, StatusEnum

# ── Text similarity ───────────────────────────────────────────────────────────

def _text_similarity(a: str, b: str) -> float:
    """TF-IDF cosine via sklearn; falls back to difflib if sklearn unavailable."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        corpus = [a, b]
        vec    = TfidfVectorizer(min_df=1, stop_words="english")
        tfidf  = vec.fit_transform(corpus)
        sim    = cosine_similarity(tfidf[0:1], tfidf[1:2])
        return float(sim[0][0])
    except Exception:
        import difflib
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ── Haversine ─────────────────────────────────────────────────────────────────

EARTH_RADIUS_M = 6_371_000.0


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance in metres between two lat/lng points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return EARTH_RADIUS_M * 2 * math.asin(math.sqrt(a))


# ── Duplicate score ───────────────────────────────────────────────────────────

DISTANCE_ZERO_SCORE_M = 150.0   # distance at which distance_score reaches 0
SEARCH_RADIUS_M       = 200.0   # candidates must be within this range
LINK_THRESHOLD        = 0.65    # minimum score to auto-link as duplicate

OPEN_STATUSES = {
    StatusEnum.Reported,
    StatusEnum.Assigned,
    StatusEnum.InProgress,
    StatusEnum.Reopened,
}


def _distance_score(dist_m: float) -> float:
    """1.0 at 0 m, linearly drops to 0.0 at DISTANCE_ZERO_SCORE_M."""
    if dist_m <= 0:
        return 1.0
    if dist_m >= DISTANCE_ZERO_SCORE_M:
        return 0.0
    return 1.0 - (dist_m / DISTANCE_ZERO_SCORE_M)


def duplicate_score(new: "Issue", existing: "Issue") -> float:
    """
    Compute a composite duplicate score between two issues.

    Formula:
        score = 0.5 × distance_score + 0.2 × same_category + 0.3 × text_similarity
    """
    dist_m = haversine(new.lat, new.lng, existing.lat, existing.lng)
    d_score = _distance_score(dist_m)
    c_score = 1.0 if new.category == existing.category else 0.0

    new_text      = f"{new.title} {new.description}"
    existing_text = f"{existing.title} {existing.description}"
    t_score       = _text_similarity(new_text, existing_text)

    return round(0.5 * d_score + 0.2 * c_score + 0.3 * t_score, 4)


# ── Candidate finder ──────────────────────────────────────────────────────────

def _nearby_open_same_category(issue: "Issue", db: "Session") -> list["Issue"]:
    """
    Fetch open issues of the same category within SEARCH_RADIUS_M using a
    bounding-box pre-filter then exact Haversine check.
    """
    # 1° latitude ≈ 111 km → delta_deg for our radius
    delta_lat = SEARCH_RADIUS_M / 111_000.0
    delta_lng = SEARCH_RADIUS_M / (111_000.0 * math.cos(math.radians(issue.lat)))

    candidates = (
        db.query(Issue)
        .filter(
            Issue.id       != issue.id,
            Issue.category == issue.category,
            Issue.status.in_(list(OPEN_STATUSES)),
            Issue.lat.between(issue.lat - delta_lat, issue.lat + delta_lat),
            Issue.lng.between(issue.lng - delta_lng, issue.lng + delta_lng),
        )
        .all()
    )

    # Exact radius filter
    return [
        c for c in candidates
        if haversine(issue.lat, issue.lng, c.lat, c.lng) <= SEARCH_RADIUS_M
    ]


def find_duplicates(new_issue: "Issue", db: "Session") -> list[tuple["Issue", float]]:
    """
    Return a list of (existing_issue, score) pairs sorted by score descending.
    Only open issues of the same category within SEARCH_RADIUS_M are considered.
    """
    candidates = _nearby_open_same_category(new_issue, db)
    scored     = [(c, duplicate_score(new_issue, c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def check_and_link_duplicate(new_issue: "Issue", db: "Session") -> None:
    """
    Run duplicate detection for a freshly created issue.
    If the best score ≥ LINK_THRESHOLD:
      - links the issue to its parent (sets parent_issue_id + duplicate_score)
      - increments the parent's affected_count
      - creates a Notification for the reporter
    """
    scored = find_duplicates(new_issue, db)
    if not scored:
        return

    best_issue, best_score = scored[0]
    if best_score < LINK_THRESHOLD:
        return

    # Link duplicate
    new_issue.parent_issue_id = best_issue.id
    new_issue.duplicate_score  = best_score
    db.add(new_issue)

    # Bump parent affected count
    best_issue.affected_count += 1
    db.add(best_issue)

    # Notify reporter
    msg = f"Potential duplicate of #{best_issue.reference_id}. Your issue has been linked."
    notification = Notification(
        user_id  = new_issue.reporter_id,
        issue_id = new_issue.id,
        message  = msg,
        is_read  = False,
    )
    db.add(notification)
    db.commit()
    db.refresh(new_issue)


# ── Similar candidates (pre-submit panel) ────────────────────────────────────

def get_similar_candidates(
    lat: float,
    lng: float,
    category: Optional[str],
    text: Optional[str],
    db: "Session",
) -> list[dict]:
    """
    Return up to 5 open issue candidates near (lat, lng) sorted by composite
    similarity score.  Used by GET /api/issues/similar before issue submission.
    """
    # Build a lightweight proxy to reuse duplicate_score logic
    class _Proxy:
        def __init__(self):
            self.lat         = lat
            self.lng         = lng
            self.title       = text or ""
            self.description = text or ""

    from app.models import CategoryEnum

    # Bounding-box pre-filter
    delta_lat = SEARCH_RADIUS_M / 111_000.0
    delta_lng = SEARCH_RADIUS_M / (111_000.0 * math.cos(math.radians(lat)))

    q = db.query(Issue).filter(
        Issue.status.in_(list(OPEN_STATUSES)),
        Issue.lat.between(lat - delta_lat, lat + delta_lat),
        Issue.lng.between(lng - delta_lng, lng + delta_lng),
    )
    if category:
        try:
            q = q.filter(Issue.category == CategoryEnum(category))
        except ValueError:
            pass

    candidates = q.limit(50).all()

    # Score each
    proxy = _Proxy()
    results = []
    for c in candidates:
        dist_m  = haversine(lat, lng, c.lat, c.lng)
        if dist_m > SEARCH_RADIUS_M:
            continue
        d_score = _distance_score(dist_m)
        c_score = 1.0 if (category and c.category.value == category) else 0.5
        t_score = _text_similarity(
            f"{proxy.title} {proxy.description}",
            f"{c.title} {c.description}",
        ) if text else 0.0
        score   = 0.5 * d_score + 0.2 * c_score + 0.3 * t_score
        thumbnail = c.photos[0].url if c.photos else None
        results.append({
            "id":           c.id,
            "reference_id": c.reference_id,
            "title":        c.title,
            "category":     c.category.value,
            "status":       c.status.value,
            "address":      c.address,
            "lat":          c.lat,
            "lng":          c.lng,
            "distance_m":   round(dist_m, 1),
            "thumbnail":    thumbnail,
            "score":        round(score, 4),
        })

    # Sort by score desc, return top 5
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]
