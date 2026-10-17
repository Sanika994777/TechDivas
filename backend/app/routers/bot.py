"""
routers/bot.py
────────────────────────────────────────────────────────────────────────────
POST /api/bot/message  {message, lang?}  →  {reply, intent, status_card|null,
                                              links, suggestions}
GET  /api/bot/suggestions               →  {items: [string]}

Flow:
  1. Scan message for a CF-YYYY-NNNNNN reference ID.
  2. If found → fetch issue → build_status_payload() → phrase_with_gemini()
     → return reply + status_card.
  3. If not found and message looks like a tracking request → ask for the ID.
  4. Otherwise → rule-based intent detection with helpful links.
  5. Gemini is used for phrasing step 2 only.  All other replies are
     deterministic templates (no per-message Gemini calls for general chat).

Rate limiting for /bot/message is handled at the infrastructure level.
The track endpoint is rate-limited separately in routers/track.py.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.models import Issue, User
from app.schemas import BotMessageOut, BotMessageRequest, BotLink
from app.services.bot import (
    build_status_payload,
    parse_reference_id,
    phrase_with_gemini,
)

router = APIRouter()

QUICK_SUGGESTIONS = [
    "How do I report a pothole?",
    "Track my complaint",
    "What is the SLA for water leaks?",
    "How are issues prioritised?",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _looks_like_tracking_request(msg: str) -> bool:
    keywords = ["track", "status", "complaint", "reference", "cf-", "cf ", "where is"]
    return any(k in msg for k in keywords)


def _rule_based_reply(msg: str) -> tuple[str, str, list[BotLink]]:
    """
    Return (reply, intent, links) using simple keyword rules.
    No Gemini involved.
    """
    if any(w in msg for w in ["report", "submit", "new issue", "pothole",
                               "garbage", "water", "streetlight", "leak"]):
        return (
            "You can report a civic issue in just a few steps — take a photo, "
            "describe the problem, and drop a pin on the map!",
            "report",
            [BotLink(label="Report an Issue", path="/report")],
        )

    if any(w in msg for w in ["sla", "days", "how long", "deadline"]):
        return (
            "SLA targets: Pothole → 7 days, Water Leak → 2 days, "
            "Garbage → 3 days, Streetlight → 5 days, Other → 5 days.",
            "sla",
            [],
        )

    if any(w in msg for w in ["priority", "score", "urgent", "critical"]):
        return (
            "Priority is calculated from Severity (40%), Community impact — "
            "upvotes (35%), and Time unresolved vs SLA (25%). "
            "Critical ≥ 75, High ≥ 55, Medium ≥ 35, Low < 35.",
            "priority",
            [],
        )

    if any(w in msg for w in ["nearby", "near me", "around", "area"]):
        return (
            "Use the Nearby page to see open civic issues on a map around you.",
            "nearby",
            [BotLink(label="Nearby Issues", path="/nearby")],
        )

    if any(w in msg for w in ["my complaints", "my issues", "my reports"]):
        return (
            "You can see all your submitted complaints and their current status "
            "on the My Complaints page.",
            "my_complaints",
            [BotLink(label="My Complaints", path="/my-complaints")],
        )

    # Fallback general reply
    return (
        "Hi! I'm the CivicFix assistant. I can help you report issues, "
        "track complaints, or explain how priorities and SLAs work. "
        "What would you like to know?",
        "general",
        [
            BotLink(label="Report Issue",    path="/report"),
            BotLink(label="Track Complaint", path="/track"),
            BotLink(label="Nearby Issues",   path="/nearby"),
        ],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/suggestions")
def bot_suggestions():
    return {"items": QUICK_SUGGESTIONS}


@router.post("/message", response_model=BotMessageOut)
async def bot_message(
    payload: BotMessageRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> BotMessageOut:
    """
    Main conversational endpoint.

    - Extracts a reference ID if present.
    - Fetches the issue and phrases a Gemini (or template) reply.
    - Falls back to rule-based intent detection for all other messages.
    - Returns status_card only when an issue was found.
    """
    msg  = (payload.message or "").strip()
    lang = (payload.lang or "en").strip() or "en"

    # ── 1. Try to find a reference ID in the message ────────────────────────
    ref_id = parse_reference_id(msg)

    if ref_id:
        issue = db.query(Issue).filter(Issue.reference_id == ref_id).first()
        if not issue:
            return BotMessageOut(
                reply=(
                    f"I couldn't find a complaint with reference ID **{ref_id}**. "
                    "Please double-check the ID or visit the Track page."
                ),
                intent="track_not_found",
                status_card=None,
                links=[BotLink(label="Track Complaint", path="/track")],
                suggestions=QUICK_SUGGESTIONS[:3],
            )

        # Build public-only payload — no PII, no coords
        status_payload = build_status_payload(issue)

        # Ask Gemini to phrase it (falls back to template on any error)
        reply = await phrase_with_gemini(
            status_payload,
            lang,
            api_key=settings.GEMINI_API_KEY,
        )

        return BotMessageOut(
            reply=reply,
            intent="track",
            status_card=status_payload,
            links=[BotLink(label="View Full Details", path=f"/track/{ref_id}")],
            suggestions=QUICK_SUGGESTIONS[:3],
        )

    # ── 2. No reference ID — ask for it if message sounds like tracking ─────
    msg_lower = msg.lower()
    if _looks_like_tracking_request(msg_lower):
        return BotMessageOut(
            reply=(
                "I'd love to look that up! Could you share your complaint's "
                "reference ID? It looks like CF-2026-000001 and was sent to you "
                "when you submitted the report."
            ),
            intent="ask_for_id",
            status_card=None,
            links=[BotLink(label="Track Complaint", path="/track")],
            suggestions=QUICK_SUGGESTIONS[:3],
        )

    # ── 3. Rule-based fallback for all other messages ───────────────────────
    reply_text, intent, links = _rule_based_reply(msg_lower)

    return BotMessageOut(
        reply=reply_text,
        intent=intent,
        status_card=None,
        links=links,
        suggestions=QUICK_SUGGESTIONS[:3],
    )
