from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.models import User
from app.schemas import BotMessageRequest, BotMessageOut, BotLink

router = APIRouter()

QUICK_SUGGESTIONS = [
    "How do I report a pothole?",
    "Track my complaint",
    "What is the SLA for water leaks?",
    "How are issues prioritised?",
]


@router.get("/suggestions")
def bot_suggestions():
    return {"items": QUICK_SUGGESTIONS}


@router.post("/message", response_model=BotMessageOut)
async def bot_message(
    payload: BotMessageRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    msg = payload.message.strip().lower()

    # Simple intent detection
    if any(w in msg for w in ["track", "status", "where", "reference", "cf-"]):
        intent = "track"
        reply = "Please go to the Track page and enter your reference ID (e.g. CF-2026-000001) to see live status updates."
        links = [BotLink(label="Track Complaint", path="/track")]

    elif any(w in msg for w in ["report", "submit", "new issue", "pothole", "garbage", "water", "streetlight"]):
        intent = "report"
        reply = "You can report a civic issue in just a few steps — take a photo, describe the problem and drop a pin on the map!"
        links = [BotLink(label="Report an Issue", path="/report")]

    elif any(w in msg for w in ["sla", "days", "how long", "time"]):
        intent = "sla"
        reply = ("SLA targets: Pothole → 7 days, Water Leak → 2 days, "
                 "Garbage → 3 days, Streetlight → 5 days, Other → 5 days.")
        links = []

    elif any(w in msg for w in ["priority", "score", "urgent"]):
        intent = "priority"
        reply = ("Priority is calculated from: Severity (40%), Community impact — upvotes (35%), "
                 "Time unresolved vs SLA (25%). Critical ≥75, High ≥55, Medium ≥35, Low <35.")
        links = []

    else:
        intent = "general"
        reply = ("Hi! I'm the CivicFix assistant. I can help you report issues, track complaints, "
                 "or explain how priorities and SLAs work. What would you like to know?")
        links = [
            BotLink(label="Report Issue",      path="/report"),
            BotLink(label="Track Complaint",   path="/track"),
            BotLink(label="Nearby Issues",     path="/nearby"),
        ]

    # Attempt Gemini for richer replies if configured
    try:
        import google.generativeai as genai
        from app.core.config import settings
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            system = (
                "You are CivicFix assistant for Pune, India. "
                "Answer only civic issue questions. Keep replies under 120 words. "
                "Do not reveal personal data or internal notes."
            )
            history = [{"role": m["role"], "parts": [m["text"]]} for m in (payload.history or [])]
            chat = model.start_chat(history=history)
            resp = chat.send_message(f"{system}\n\nUser: {payload.message}")
            reply = resp.text
    except Exception:
        pass  # stick with rule-based reply

    return BotMessageOut(
        reply=reply,
        intent=intent,
        links=links,
        suggestions=QUICK_SUGGESTIONS[:3],
    )
