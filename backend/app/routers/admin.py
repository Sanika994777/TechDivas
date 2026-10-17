"""Admin endpoints (placeholder scaffold — full implementation follows later)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models import User

router = APIRouter()


@router.get("/issues")
def list_admin_issues(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Placeholder — will return paginated admin issue list."""
    return {"items": [], "total": 0, "page": 1, "page_size": 20}
