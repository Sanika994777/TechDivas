"""
routers/track.py
────────────────────────────────────────────────────────────────────────────
GET /api/track/{reference_id}

Public endpoint — no auth required.

Rate-limited to 20 requests per minute per IP via a simple in-memory
sliding-window counter (resets every 60 s window).  Returns HTTP 429
with a friendly message on breach.

Response contract (no PII, no exact coordinates, no worker names):
  reference_id, status, priority_label, category, area, team,
  last_update {note, time}, days_open, sla_remaining_or_overdue,
  has_after_photo, steps []
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Issue, StatusEnum
from app.schemas import TrackOut, TrackStep
from app.services.bot import SLA_DAYS, build_status_payload

router = APIRouter()

# ── In-memory rate limiter (20 req / 60 s per IP) ────────────────────────────

_RATE_LIMIT   = 20          # max requests per window
_WINDOW_SECS  = 60          # sliding window in seconds

# {ip: [(timestamp, count), ...]}  — one entry per window
_counters: dict[str, list[float]] = defaultdict(list)

STATUS_STEPS = ["Reported", "Assigned", "In Progress", "Resolved"]


def _check_rate_limit(ip: str) -> None:
    """
    Raise HTTP 429 if *ip* has made ≥ _RATE_LIMIT calls in the last
    _WINDOW_SECS seconds.  Modifies _counters in-place.
    """
    now = time.monotonic()
    window_start = now - _WINDOW_SECS

    # Drop timestamps older than the current window
    _counters[ip] = [t for t in _counters[ip] if t > window_start]

    if len(_counters[ip]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                "You've made too many requests. "
                f"Please wait a moment — limit is {_RATE_LIMIT} requests per minute. "
                "Try again shortly."
            ),
        )

    _counters[ip].append(now)


def _is_done(current: str, step: str) -> bool:
    order = {"Reported": 0, "Assigned": 1, "In Progress": 2, "Resolved": 3, "Reopened": 2}
    return order.get(current, 0) >= order.get(step, 99)


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/track/{reference_id}", response_model=TrackOut)
def track_issue(
    reference_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackOut:
    """
    Public complaint status lookup.

    Returns only public fields — no reporter info, no exact coordinates,
    no worker names, no internal notes or scores.
    Rate-limited to 20 requests/min per IP.
    """
    # ── Rate limit ──────────────────────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # ── Normalise and look up ───────────────────────────────────────────────
    ref = reference_id.strip().upper()
    issue = db.query(Issue).filter(Issue.reference_id == ref).first()
    if not issue:
        raise HTTPException(404, "Complaint not found. Please check the reference ID.")

    # ── Build public payload (no PII, no coords) ────────────────────────────
    payload = build_status_payload(issue)

    # ── Steps timeline ──────────────────────────────────────────────────────
    steps = [
        TrackStep(label=s, done=_is_done(issue.status.value, s))
        for s in STATUS_STEPS
    ]

    return TrackOut(
        reference_id          = payload["reference_id"],
        status                = payload["status"],
        priority_label        = payload["priority_label"],
        category              = payload["category"],
        area                  = payload["area"],
        team                  = payload["team"],
        last_update           = payload["last_update"],
        days_open             = payload["days_open"],
        sla_text              = payload["sla_remaining_or_overdue"],
        has_after_photo       = payload["has_after_photo"],
        steps                 = steps,
    )
