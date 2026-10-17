from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Notification, User
from app.schemas import NotificationListOut, NotificationOut

router = APIRouter()


@router.get("", response_model=NotificationListOut)
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
            id=n.id,
            issue_id=n.issue_id,
            reference_id=ref,
            message=n.message,
            is_read=n.is_read,
            created_at=n.created_at,
        ))
    return NotificationListOut(items=out, unread_count=unread)


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(404, "Notification not found.")
    notif.is_read = True
    db.commit()
    return {"ok": True}
