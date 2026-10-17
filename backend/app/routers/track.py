from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.models import Issue, StatusEnum
from app.schemas import TrackOut, TrackStep

router = APIRouter()

SLA_DAYS = {
    "Pothole": 7, "Water Leak": 2, "Garbage": 3, "Streetlight": 5, "Other": 5,
}

STATUS_STEPS = ["Reported", "Assigned", "In Progress", "Resolved"]


@router.get("/track/{reference_id}", response_model=TrackOut)
def track_issue(reference_id: str, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.reference_id == reference_id.upper()).first()
    if not issue:
        raise HTTPException(404, "Complaint not found.")

    now = datetime.now(timezone.utc)
    created = issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at.tzinfo is None else issue.created_at
    days_open = (now - created).days
    sla_days = SLA_DAYS.get(issue.category.value, 5)
    remaining = max(0, sla_days - days_open)
    if remaining == 0 and issue.status != StatusEnum.Resolved:
        sla_text = "⚠ Overdue"
    elif issue.status == StatusEnum.Resolved:
        sla_text = "Resolved ✓"
    else:
        sla_text = f"{remaining} day(s) remaining"

    last = issue.timeline[-1] if issue.timeline else None
    last_update = None
    if last:
        last_update = {"note": last.note, "time": last.created_at.isoformat()}

    has_after = any(p.kind.value == "after" for p in issue.photos)
    steps = [
        TrackStep(label=s, done=_is_done(issue.status.value, s))
        for s in STATUS_STEPS
    ]

    return TrackOut(
        reference_id=issue.reference_id,
        status=issue.status.value,
        priority_label=_priority_label(issue),
        category=issue.category.value,
        area=issue.address.split(",")[0],
        team=issue.team.name if issue.team else None,
        last_update=last_update,
        days_open=days_open,
        sla_text=sla_text,
        has_after_photo=has_after,
        steps=steps,
    )


def _is_done(current: str, step: str) -> bool:
    order = {"Reported": 0, "Assigned": 1, "In Progress": 2, "Resolved": 3, "Reopened": 2}
    return order.get(current, 0) >= order.get(step, 99)


def _priority_label(issue: Issue) -> str:
    from datetime import timezone as tz
    now = datetime.now(tz.utc)
    created = issue.created_at.replace(tzinfo=tz.utc) if issue.created_at.tzinfo is None else issue.created_at
    sla = SLA_DAYS.get(issue.category.value, 5)
    days = (now - created).days
    time_score = min(100, (days / sla) * 100)
    sev_score = (issue.severity / 5) * 100
    ci_score = min(100, issue.affected_count * 5)
    score = sev_score * 0.40 + ci_score * 0.35 + time_score * 0.25
    if score >= 75: return "Critical"
    if score >= 55: return "High"
    if score >= 35: return "Medium"
    return "Low"
