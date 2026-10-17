"""
Admin router — admin-only endpoints:

  GET  /api/admin/issues                   paginated list, priority-sorted, filterable
  POST /api/admin/issues/{id}/assign       assign team → status Assigned + notify reporter
  GET  /api/admin/stats?period=7|30|90     analytics dashboard data (pure SQL aggregation)
  GET  /api/admin/duplicates               issues with parent_issue_id set
  POST /api/admin/duplicates/{id}/merge    confirm link, adjust counts, recalc priority
  POST /api/admin/duplicates/{id}/dismiss  clear link, decrement parent count, recalc

All routes require admin role.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, cast, func
from sqlalchemy.orm import Session
from sqlalchemy.types import Date

from app.core.database import get_db
from app.core.deps import require_admin
from app.models import CategoryEnum, Issue, StatusEnum, Team, User
from app.routers.notifications import create_notification
from app.routers.issues import issue_to_summary, issue_to_detail
from app.services import priority as priority_svc

router = APIRouter()

# ── Category → suggested team mapping ────────────────────────────────────────
CATEGORY_TEAM: dict[str, str] = {
    "Pothole":     "Roads",
    "Water Leak":  "Water",
    "Garbage":     "Sanitation & Electrical",
    "Streetlight": "Sanitation & Electrical",
    "Other":       "Roads",
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class AssignRequest(BaseModel):
    team_id: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _suggested_team(issue: Issue, db: Session) -> Optional[dict]:
    """Return the auto-suggested team dict for the issue's category, or None."""
    team_name = CATEGORY_TEAM.get(issue.category.value)
    if not team_name:
        return None
    team = db.query(Team).filter(Team.name == team_name).first()
    if not team:
        return None
    return {"id": team.id, "name": team.name}


def _enrich(issue: Issue, db: Session) -> dict:
    """Return issue summary dict enriched with suggested_team."""
    s = issue_to_summary(issue)
    d = s.model_dump()
    d["suggested_team"] = _suggested_team(issue, db)
    return d


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/issues", response_model=dict)
def admin_list_issues(
    sort:     str           = "priority",      # "priority" | "created_at"
    status:   Optional[str] = None,
    category: Optional[str] = None,
    team_id:  Optional[int] = None,
    page:     int           = 1,
    page_size: int          = 20,
    current_user: User      = Depends(require_admin),
    db: Session             = Depends(get_db),
):
    """
    Admin issue list. Default sort: priority descending (scores recalculated on load).
    Supports filters: status, category, team_id.
    """
    q = db.query(Issue)

    if status:
        try:
            q = q.filter(Issue.status == StatusEnum(status))
        except ValueError:
            raise HTTPException(422, f"Invalid status: {status}")
    if category:
        q = q.filter(Issue.category == category)
    if team_id:
        q = q.filter(Issue.team_id == team_id)

    # Fetch all matching for recalc, then paginate
    issues = q.all()

    # Recalculate priority scores in bulk
    for issue in issues:
        result = priority_svc.calculate_priority(issue)
        if abs(issue.priority_score - result.score) > 0.5:
            issue.priority_score = result.score
            db.add(issue)
    db.commit()

    # Sort
    if sort == "priority":
        issues.sort(key=lambda i: i.priority_score, reverse=True)
    else:
        issues.sort(key=lambda i: i.created_at, reverse=True)

    # Paginate
    total  = len(issues)
    start  = (page - 1) * page_size
    paged  = issues[start : start + page_size]

    # Get all teams for the sidebar
    teams  = db.query(Team).all()

    return {
        "items":     [_enrich(i, db) for i in paged],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "teams":     [{"id": t.id, "name": t.name} for t in teams],
    }


@router.post("/issues/{issue_id}/assign", response_model=dict)
def admin_assign_issue(
    issue_id: int,
    payload:  AssignRequest,
    current_user: User = Depends(require_admin),
    db: Session        = Depends(get_db),
):
    """
    Assign an issue to a team.
    - Sets issue.team_id and moves status to Assigned (if currently Reported).
    - Creates a StatusHistory row.
    - Notifies the reporter.
    - Returns the updated issue with suggested_team included.
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found.")

    team = db.get(Team, payload.team_id)
    if not team:
        raise HTTPException(404, f"Team {payload.team_id} not found.")

    issue.team_id = team.id

    # Only auto-advance status when issue is still in Reported state
    if issue.status == StatusEnum.Reported:
        issue.status = StatusEnum.Assigned
        from app.models import StatusHistory
        db.add(StatusHistory(
            issue_id   = issue.id,
            status     = StatusEnum.Assigned,
            note       = f"Assigned to team '{team.name}' by admin.",
            actor_role = "admin",
            changed_by = current_user.id,
        ))
        # Notify reporter
        create_notification(
            user_id  = issue.reporter_id,
            message  = (
                f"Your issue #{issue.reference_id} has been assigned to the "
                f"'{team.name}' team and is now being processed."
            ),
            issue_id = issue.id,
            db       = db,
        )

    db.add(issue)
    db.commit()
    db.refresh(issue)
    priority_svc.recalculate_and_save(issue, db)
    db.refresh(issue)

    return {
        "ok":            True,
        "issue":         _enrich(issue, db),
        "suggested_team": _suggested_team(issue, db),
    }


# ── Stats ──────────────────────────────────────────────────────────────────────

# SLA in hours per category (matches API_CONTRACT.md)
_SLA_HOURS: dict[str, int] = {
    "Pothole":     7  * 24,   # 168 h
    "Water Leak":  2  * 24,   # 48 h
    "Garbage":     3  * 24,   # 72 h
    "Streetlight": 5  * 24,   # 120 h
    "Other":       5  * 24,   # 120 h
}

_OPEN_STATUSES = [
    StatusEnum.Reported,
    StatusEnum.Assigned,
    StatusEnum.InProgress,
    StatusEnum.Reopened,
]


@router.get("/stats", response_model=dict)
def admin_stats(
    period: int         = Query(30, description="Lookback window in days (7 | 30 | 90)"),
    current_user: User  = Depends(require_admin),
    db: Session         = Depends(get_db),
):
    """
    Analytics dashboard data — all aggregation done in SQL.

    Returns:
      kpis                  – total, open, resolved, avg_resolution_hours, overdue_count
      by_category           – [{category, count}]  (all time, descending)
      by_status             – [{status, count}]     (all time)
      daily_trend           – last <period> days [{date, reported, resolved}] zero-filled
      resolution_by_category– [{category, avg_hours}]  resolved issues only
      resolution_by_team    – [{team, avg_hours}]       resolved issues with a team
    """
    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=period)

    # ── 1. KPI — total & open & resolved ─────────────────────────────────────
    total    = db.query(func.count(Issue.id)).scalar() or 0
    open_cnt = (
        db.query(func.count(Issue.id))
        .filter(Issue.status.in_(_OPEN_STATUSES))
        .scalar() or 0
    )
    resolved_cnt = (
        db.query(func.count(Issue.id))
        .filter(Issue.status == StatusEnum.Resolved)
        .scalar() or 0
    )

    # ── 2. KPI — avg resolution hours (SQL) ──────────────────────────────────
    #   epoch gives seconds; divide by 3600 → hours.
    avg_hours_raw = (
        db.query(
            func.avg(
                func.extract("epoch", Issue.resolved_at - Issue.created_at)
            )
        )
        .filter(
            Issue.status == StatusEnum.Resolved,
            Issue.resolved_at.isnot(None),
        )
        .scalar()
    )
    avg_resolution_hours = round(float(avg_hours_raw or 0.0) / 3600, 1)

    # ── 3. KPI — overdue count ────────────────────────────────────────────────
    # One SQL scalar per category → sum in Python (5 fast queries, no ORM hydration)
    overdue_count = 0
    for cat_enum, sla_h in _SLA_HOURS.items():
        cat = CategoryEnum(cat_enum)
        n = (
            db.query(func.count(Issue.id))
            .filter(
                Issue.status.in_(_OPEN_STATUSES),
                Issue.category == cat,
                # age in seconds > SLA in seconds
                func.extract("epoch", now - Issue.created_at) > sla_h * 3600,
            )
            .scalar() or 0
        )
        overdue_count += n

    # ── 4. By category ────────────────────────────────────────────────────────
    by_cat_rows = (
        db.query(Issue.category, func.count(Issue.id).label("cnt"))
        .group_by(Issue.category)
        .order_by(func.count(Issue.id).desc())
        .all()
    )
    by_category = [{"category": r.category.value, "count": r.cnt} for r in by_cat_rows]

    # ── 5. By status ──────────────────────────────────────────────────────────
    by_status_rows = (
        db.query(Issue.status, func.count(Issue.id).label("cnt"))
        .group_by(Issue.status)
        .order_by(func.count(Issue.id).desc())
        .all()
    )
    by_status = [{"status": r.status.value, "count": r.cnt} for r in by_status_rows]

    # ── 6. Daily trend ────────────────────────────────────────────────────────
    # Two SQL GROUP-BY queries, then zero-fill in Python.

    reported_rows = (
        db.query(
            cast(Issue.created_at, Date).label("day"),
            func.count(Issue.id).label("cnt"),
        )
        .filter(Issue.created_at >= cutoff)
        .group_by("day")
        .all()
    )
    resolved_rows = (
        db.query(
            cast(Issue.resolved_at, Date).label("day"),
            func.count(Issue.id).label("cnt"),
        )
        .filter(
            Issue.resolved_at >= cutoff,
            Issue.resolved_at.isnot(None),
        )
        .group_by("day")
        .all()
    )

    reported_map  = {str(r.day): r.cnt for r in reported_rows}
    resolved_map  = {str(r.day): r.cnt for r in resolved_rows}

    daily_trend: list[dict] = []
    for offset in range(period):
        d = (now - timedelta(days=period - 1 - offset)).date()
        ds = str(d)
        daily_trend.append({
            "date":     ds,
            "reported": reported_map.get(ds, 0),
            "resolved": resolved_map.get(ds, 0),
        })

    # ── 7. Resolution by category ─────────────────────────────────────────────
    res_by_cat_rows = (
        db.query(
            Issue.category,
            (
                func.avg(
                    func.extract("epoch", Issue.resolved_at - Issue.created_at)
                )
            ).label("avg_secs"),
        )
        .filter(
            Issue.status == StatusEnum.Resolved,
            Issue.resolved_at.isnot(None),
        )
        .group_by(Issue.category)
        .order_by(Issue.category)
        .all()
    )
    resolution_by_category = [
        {"category": r.category.value, "avg_hours": round(float(r.avg_secs or 0) / 3600, 1)}
        for r in res_by_cat_rows
    ]

    # ── 8. Resolution by team ─────────────────────────────────────────────────
    res_by_team_rows = (
        db.query(
            Team.name.label("team_name"),
            (
                func.avg(
                    func.extract("epoch", Issue.resolved_at - Issue.created_at)
                )
            ).label("avg_secs"),
        )
        .join(Team, Issue.team_id == Team.id)
        .filter(
            Issue.status == StatusEnum.Resolved,
            Issue.resolved_at.isnot(None),
            Issue.team_id.isnot(None),
        )
        .group_by(Team.name)
        .order_by(Team.name)
        .all()
    )
    resolution_by_team = [
        {"team": r.team_name, "avg_hours": round(float(r.avg_secs or 0) / 3600, 1)}
        for r in res_by_team_rows
    ]

    # ── Assemble ──────────────────────────────────────────────────────────────
    return {
        "period_days": period,
        "kpis": {
            "total":                total,
            "open":                 open_cnt,
            "resolved":             resolved_cnt,
            "avg_resolution_hours": avg_resolution_hours,
            "overdue_count":        overdue_count,
        },
        "by_category":             by_category,
        "by_status":               by_status,
        "daily_trend":             daily_trend,
        "resolution_by_category":  resolution_by_category,
        "resolution_by_team":      resolution_by_team,
    }


# ── Duplicate management ──────────────────────────────────────────────────────

@router.get("/duplicates", response_model=dict)
def admin_list_duplicates(
    current_user: User = Depends(require_admin),
    db: Session        = Depends(get_db),
):
    """
    List all issues that have been linked as duplicates (parent_issue_id is set).
    Returns both the duplicate child and its parent for context.
    """
    children = (
        db.query(Issue)
        .filter(Issue.parent_issue_id.isnot(None))
        .order_by(Issue.created_at.desc())
        .all()
    )

    items = []
    for child in children:
        parent = db.get(Issue, child.parent_issue_id)
        items.append({
            "child":  issue_to_summary(child).model_dump(),
            "parent": issue_to_summary(parent).model_dump() if parent else None,
            "duplicate_score": child.duplicate_score,
        })

    return {"items": items, "total": len(items)}


@router.post("/duplicates/{issue_id}/merge", response_model=dict)
def admin_merge_duplicate(
    issue_id: int,
    current_user: User = Depends(require_admin),
    db: Session        = Depends(get_db),
):
    """
    Confirm the duplicate link:
    - Ensures parent_issue_id is set.
    - Increments parent.affected_count by 1 (mark explicitly confirmed merge).
    - Recalculates priority on both parent and child.
    """
    child = db.get(Issue, issue_id)
    if not child:
        raise HTTPException(404, "Issue not found.")
    if not child.parent_issue_id:
        raise HTTPException(422, "This issue has no duplicate link to merge.")

    parent = db.get(Issue, child.parent_issue_id)
    if not parent:
        raise HTTPException(404, "Parent issue not found.")

    parent.affected_count += 1
    db.add(parent)
    db.commit()

    priority_svc.recalculate_and_save(parent, db)
    priority_svc.recalculate_and_save(child, db)
    db.refresh(parent)
    db.refresh(child)

    return {
        "ok":     True,
        "parent": issue_to_summary(parent).model_dump(),
        "child":  issue_to_summary(child).model_dump(),
    }


@router.post("/duplicates/{issue_id}/dismiss", response_model=dict)
def admin_dismiss_duplicate(
    issue_id: int,
    current_user: User = Depends(require_admin),
    db: Session        = Depends(get_db),
):
    """
    Dismiss the duplicate link:
    - Clears child.parent_issue_id and child.duplicate_score.
    - Decrements parent.affected_count by 1 (min 0).
    - Recalculates priority on parent.
    """
    child = db.get(Issue, issue_id)
    if not child:
        raise HTTPException(404, "Issue not found.")
    if not child.parent_issue_id:
        raise HTTPException(422, "This issue has no duplicate link to dismiss.")

    parent = db.get(Issue, child.parent_issue_id)

    # Clear link on child
    child.parent_issue_id = None
    child.duplicate_score  = None
    db.add(child)

    # Decrement parent count
    if parent:
        parent.affected_count = max(0, parent.affected_count - 1)
        db.add(parent)

    db.commit()

    if parent:
        priority_svc.recalculate_and_save(parent, db)
        db.refresh(parent)

    db.refresh(child)

    return {
        "ok":     True,
        "child":  issue_to_summary(child).model_dump(),
        "parent": issue_to_summary(parent).model_dump() if parent else None,
    }
