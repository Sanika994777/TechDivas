"""
Notifications router
  GET  /api/notifications              list for current user
  POST /api/notifications/{id}/read    mark as read

Also exports create_notification() so other modules can create notifications
without importing the full router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Notification, User
from app.schemas import NotificationListOut, NotificationOut

router = APIRouter()


# ── Helper (importable by other modules) ──────────────────────────────────────

def create_notification(
    user_id: int,
    message: str,
    db: Session,
    issue_id: int | None = None,
) -> Notification:
    """
    Create and flush a Notification row.
    Caller is responsible for db.commit().
    """
    n = Notification(
        user_id  = user_id,
        issue_id = issue_id,
        message  = message,
        is_read  = False,
    )
    db.add(n)
    db.flush()
    return n


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=NotificationListOut)
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the most recent 50 notifications for the authenticated user."""
    items = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    unread = sum(1 for n in items if not n.is_read)

    out = []
    for n in items:
        ref = n.issue.reference_id if n.issue else None
        out.append(NotificationOut(
            id           = n.id,
            issue_id     = n.issue_id,
            reference_id = ref,
            message      = n.message,
            is_read      = n.is_read,
            created_at   = n.created_at,
        ))
    return NotificationListOut(items=out, unread_count=unread)


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read. Returns 404 if not found or not owned."""
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(404, "Notification not found.")
    notif.is_read = True
    db.commit()
    return {"ok": True}
