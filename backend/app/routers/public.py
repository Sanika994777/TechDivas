from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.models import Issue, StatusEnum
from app.schemas import PublicStatsOut, RecentResolvedItem

router = APIRouter()


@router.get("/stats", response_model=PublicStatsOut)
def public_stats(db: Session = Depends(get_db)):
    total = db.query(Issue).count()
    resolved = db.query(Issue).filter(Issue.status == StatusEnum.Resolved).count()

    resolved_issues = db.query(Issue).filter(
        Issue.status == StatusEnum.Resolved,
        Issue.resolved_at.isnot(None),
    ).all()
    avg_days = 0.0
    if resolved_issues:
        def _days(i):
            r = i.resolved_at.replace(tzinfo=timezone.utc) if i.resolved_at.tzinfo is None else i.resolved_at
            c = i.created_at.replace(tzinfo=timezone.utc) if i.created_at.tzinfo is None else i.created_at
            return (r - c).days
        avg_days = round(sum(_days(i) for i in resolved_issues) / len(resolved_issues), 1)

    return PublicStatsOut(total=total, resolved=resolved, avg_resolution_days=avg_days)


@router.get("/recent-resolved")
def recent_resolved(limit: int = Query(5, le=20), db: Session = Depends(get_db)):
    issues = (
        db.query(Issue)
        .filter(Issue.status == StatusEnum.Resolved)
        .order_by(Issue.resolved_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for i in issues:
        before = next((p.url for p in i.photos if p.kind.value == "before"), None)
        after  = next((p.url for p in i.photos if p.kind.value == "after"),  None)
        items.append(RecentResolvedItem(
            reference_id=i.reference_id,
            title=i.title,
            category=i.category.value,
            area=i.address.split(",")[0],
            before_url=before,
            after_url=after,
            resolved_at=i.resolved_at,
        ))
    return {"items": items}
