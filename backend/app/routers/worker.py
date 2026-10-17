"""
Worker router
  GET  /api/worker/issues               issues assigned to the worker's team
  POST /api/worker/issues/{id}/status   update status with optional after-photo

Transitions allowed:
  Assigned   → In Progress   (note optional, photo optional)
  In Progress → Resolved     (note REQUIRED, after-photo REQUIRED)

On Resolved:
  - resolved_at is set
  - IssuePhoto row added (kind=after)
  - StatusHistory row written
  - Notifications sent to: reporter + every upvoter
  - Priority recalculated

Role guard: worker or admin only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_worker
from app.models import (
    Issue, IssuePhoto, PhotoKindEnum, StatusEnum, StatusHistory, Upvote, User,
)
from app.routers.notifications import create_notification
from app.services import priority as priority_svc
from app.services.cloudinary_service import validate_and_upload

# reuse summary/detail serialisers from issues router
from app.routers.issues import issue_to_detail, issue_to_summary

router = APIRouter()

# ── Valid transitions ──────────────────────────────────────────────────────────

ALLOWED_TRANSITIONS: dict[StatusEnum, set[StatusEnum]] = {
    StatusEnum.Assigned:   {StatusEnum.InProgress},
    StatusEnum.InProgress: {StatusEnum.Resolved},
    StatusEnum.Reopened:   {StatusEnum.InProgress},   # reopen → back to work
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/issues", response_model=dict)
def worker_list_issues(
    status: Optional[str] = None,
    current_user: User = Depends(require_worker),
    db: Session = Depends(get_db),
):
    """
    Return all issues belonging to the worker's team, optionally filtered
    by status. Issues with no team assignment are excluded.
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=400,
            detail="Your account is not assigned to a team. Contact an admin.",
        )

    q = db.query(Issue).filter(Issue.team_id == current_user.team_id)
    if status:
        try:
            q = q.filter(Issue.status == StatusEnum(status))
        except ValueError:
            valid = [s.value for s in StatusEnum]
            raise HTTPException(422, f"Invalid status. Valid values: {valid}")

    issues = q.order_by(Issue.priority_score.desc()).all()
    return {
        "team": current_user.team.name if current_user.team else None,
        "items": [issue_to_summary(i) for i in issues],
        "total": len(issues),
    }


@router.post("/issues/{issue_id}/status", response_model=dict)
async def worker_update_status(
    issue_id: int,
    status: str            = Form(...),
    note: Optional[str]    = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: User     = Depends(require_worker),
    db: Session            = Depends(get_db),
):
    """
    Advance an issue through its workflow.

    Transitions:
      Assigned / Reopened → In Progress   (note optional, photo optional)
      In Progress         → Resolved      (note REQUIRED, after-photo REQUIRED)

    On Resolved:
      - resolved_at is stamped
      - After photo saved to Cloudinary
      - StatusHistory row written
      - Notifications sent to reporter + all upvoters
      - Priority score recalculated
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found.")

    # ── Team guard ────────────────────────────────────────────────────────
    if issue.team_id != current_user.team_id:
        raise HTTPException(403, "This issue belongs to a different team.")

    # ── Parse target status ───────────────────────────────────────────────
    try:
        new_status = StatusEnum(status)
    except ValueError:
        valid = [s.value for s in StatusEnum]
        raise HTTPException(422, f"Invalid status '{status}'. Valid: {valid}")

    # ── Validate transition ───────────────────────────────────────────────
    allowed = ALLOWED_TRANSITIONS.get(issue.status, set())
    if new_status not in allowed:
        raise HTTPException(
            422,
            f"Cannot transition from '{issue.status.value}' to '{new_status.value}'. "
            f"Allowed targets from current state: {[s.value for s in allowed] or 'none'}.",
        )

    # ── Resolved-specific validation ──────────────────────────────────────
    after_url: Optional[str] = None
    if new_status == StatusEnum.Resolved:
        if not note or not note.strip():
            raise HTTPException(
                422,
                "A resolution note is required when marking an issue as Resolved.",
            )
        # Check if a photo is already provided in this request or already exists
        has_existing_after = any(
            p.kind == PhotoKindEnum.after for p in issue.photos
        )
        if photo and photo.filename:
            # Upload the after photo
            after_url = await validate_and_upload(photo, folder="civicfix/resolved")
        elif not has_existing_after:
            raise HTTPException(
                422,
                "An after-photo is required when marking an issue as Resolved. "
                "Please attach a photo showing the resolved state.",
            )

    # ── Apply status change ───────────────────────────────────────────────
    issue.status = new_status
    if new_status == StatusEnum.Resolved:
        issue.resolved_at = datetime.now(timezone.utc)

    # ── Attach after-photo ────────────────────────────────────────────────
    if after_url:
        db.add(IssuePhoto(
            issue_id   = issue.id,
            url        = after_url,
            kind       = PhotoKindEnum.after,
            created_at = datetime.now(timezone.utc),
        ))

    # ── StatusHistory row ─────────────────────────────────────────────────
    db.add(StatusHistory(
        issue_id   = issue.id,
        status     = new_status,
        note       = note or f"Status updated to {new_status.value} by field worker.",
        photo_url  = after_url,
        actor_role = "worker",
        changed_by = current_user.id,
    ))

    db.add(issue)
    db.flush()

    # ── Notifications (on Resolved) ───────────────────────────────────────
    if new_status == StatusEnum.Resolved:
        msg = (
            f"Great news! Your issue #{issue.reference_id} — '{issue.title[:60]}' "
            f"has been Resolved. Please confirm satisfaction in the app."
        )
        # Reporter
        create_notification(
            user_id  = issue.reporter_id,
            message  = msg,
            issue_id = issue.id,
            db       = db,
        )
        # All upvoters (excluding reporter to avoid double notification)
        upvoter_ids = (
            db.query(Upvote.user_id)
            .filter(
                Upvote.issue_id == issue.id,
                Upvote.user_id  != issue.reporter_id,
            )
            .all()
        )
        for (uid,) in upvoter_ids:
            create_notification(
                user_id  = uid,
                message  = (
                    f"Issue #{issue.reference_id} you upvoted has been Resolved: "
                    f"'{issue.title[:60]}'"
                ),
                issue_id = issue.id,
                db       = db,
            )

    db.commit()
    db.refresh(issue)

    # ── Recalculate priority ──────────────────────────────────────────────
    priority_svc.recalculate_and_save(issue, db)
    db.refresh(issue)

    return {
        "ok":    True,
        "issue": issue_to_detail(issue, current_user, db).model_dump(),
    }
