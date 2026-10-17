"""
Issues router — citizen-facing endpoints:
  POST   /api/issues                     submit issue (multipart/form-data)
  GET    /api/issues/nearby              map view
  GET    /api/issues/mine                my complaints
  GET    /api/issues/{id}                detail (photos + timeline + priority)
  POST   /api/issues/{id}/upvote         toggle upvote
  POST   /api/issues/{id}/feedback       satisfied / reopen
  POST   /api/issues/analyze-photo       AI photo analysis
  GET    /api/issues/similar             duplicate check
  GET    /api/geo/reverse                reverse geocode
"""
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional, require_citizen
from app.models import (
    CategoryEnum, Issue, IssuePhoto, PhotoKindEnum,
    SatisfactionEnum, StatusEnum, StatusHistory, Team, Upvote, User,
)
from app.schemas import (
    AnalyzePhotoOut, IssueDetailOut, IssueSummaryOut, MyIssueStats,
    MyIssuesOut, PhotoOut, PriorityComponents, PriorityOut, ReverseGeoOut,
    TeamOut, TimelineItemOut, UpvoteOut, FeedbackRequest,
)
from app.services.cloudinary_service import upload_many

router = APIRouter()

# ── SLA config ────────────────────────────────────────────────────────────────
SLA_DAYS = {
    "Pothole": 7, "Water Leak": 2, "Garbage": 3, "Streetlight": 5, "Other": 5,
}

CATEGORY_TEAM = {
    "Pothole": "Roads", "Water Leak": "Water",
    "Garbage": "Sanitation & Electrical", "Streetlight": "Sanitation & Electrical",
}


# ── Priority helpers ──────────────────────────────────────────────────────────

def compute_priority(issue: Issue) -> PriorityOut:
    now = datetime.now(timezone.utc)
    created = (
        issue.created_at.replace(tzinfo=timezone.utc)
        if issue.created_at.tzinfo is None
        else issue.created_at
    )
    sla_days   = SLA_DAYS.get(issue.category.value, 5)
    days_open  = (now - created).days
    time_score = min(100.0, (days_open / sla_days) * 100)

    sev_score = (issue.severity / 5) * 100
    ci_score  = min(100.0, issue.affected_count * 5)

    score = round(sev_score * 0.40 + ci_score * 0.35 + time_score * 0.25, 1)

    if score >= 75:
        label = "Critical"
    elif score >= 55:
        label = "High"
    elif score >= 35:
        label = "Medium"
    else:
        label = "Low"

    return PriorityOut(
        score=score,
        label=label,
        components=PriorityComponents(
            severity=round(sev_score, 1),
            community_impact=round(ci_score, 1),
            time_unresolved=round(time_score, 1),
        ),
    )


def make_reference_id(db: Session) -> str:
    """Generate next CF-YYYY-NNNNNN reference ID (not collision-safe for concurrent inserts,
    but fine for a hackathon single-instance deployment)."""
    year  = datetime.now(timezone.utc).year
    count = db.query(func.count(Issue.id)).scalar() or 0
    return f"CF-{year}-{count + 1:06d}"


# ── Serialisers ───────────────────────────────────────────────────────────────

def issue_to_summary(issue: Issue, distance_m: Optional[float] = None) -> IssueSummaryOut:
    thumbnail = issue.photos[0].url if issue.photos else None
    return IssueSummaryOut(
        id=issue.id,
        reference_id=issue.reference_id,
        title=issue.title,
        category=issue.category.value,
        status=issue.status.value,
        address=issue.address,
        lat=issue.lat,
        lng=issue.lng,
        distance_m=distance_m,
        affected_count=issue.affected_count,
        thumbnail=thumbnail,
        priority=compute_priority(issue),
        created_at=issue.created_at,
    )


def issue_to_detail(
    issue: Issue,
    current_user: Optional[User] = None,
    db: Optional[Session] = None,
) -> IssueDetailOut:
    summary = issue_to_summary(issue)

    has_upvoted = False
    if current_user and db:
        has_upvoted = (
            db.query(Upvote)
            .filter_by(issue_id=issue.id, user_id=current_user.id)
            .first()
        ) is not None

    photos = [PhotoOut(url=p.url, kind=p.kind.value) for p in issue.photos]
    team   = TeamOut(id=issue.team.id, name=issue.team.name) if issue.team else None
    timeline = [
        TimelineItemOut(
            status=t.status.value,
            note=t.note,
            photo_url=t.photo_url,
            actor_role=t.actor_role,
            created_at=t.created_at,
        )
        for t in issue.timeline
    ]

    return IssueDetailOut(
        **summary.model_dump(),
        description=issue.description,
        photos=photos,
        team=team,
        parent_issue_id=issue.parent_issue_id,
        timeline=timeline,
        satisfaction=issue.satisfaction.value if issue.satisfaction else None,
        resolved_at=issue.resolved_at,
        has_upvoted=has_upvoted,
        is_owner=current_user is not None and issue.reporter_id == current_user.id,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze-photo", response_model=AnalyzePhotoOut)
async def analyze_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(require_citizen),
):
    """AI photo analysis — Gemini with keyword fallback."""
    try:
        import google.generativeai as genai
        from app.core.config import settings
        genai.configure(api_key=settings.GEMINI_API_KEY)
        image_data = await photo.read()
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            "Analyze this civic issue photo. Respond in JSON only with keys: "
            "suggested_category (one of: Pothole, Water Leak, Garbage, Streetlight, Other), "
            "severity (integer 1-5), short_description (max 100 chars).",
            {"mime_type": photo.content_type, "data": image_data},
        ])
        import json, re
        raw = response.text
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(match.group()) if match else {}
        return AnalyzePhotoOut(
            suggested_category=data.get("suggested_category", "Other"),
            severity=int(data.get("severity", 3)),
            short_description=data.get("short_description", "Civic issue detected."),
        )
    except Exception:
        return AnalyzePhotoOut(
            suggested_category="Other",
            severity=3,
            short_description="Photo uploaded. Please fill in details manually.",
        )


@router.get("/nearby", response_model=dict)
def get_nearby(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(5000),
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return issues within radius metres using the Haversine formula in SQL."""
    haversine = text("""
        6371000 * 2 * ASIN(SQRT(
          POWER(SIN(RADIANS(:lat - issues.lat) / 2), 2) +
          COS(RADIANS(:lat)) * COS(RADIANS(issues.lat)) *
          POWER(SIN(RADIANS(:lng - issues.lng) / 2), 2)
        ))
    """).bindparams(lat=lat, lng=lng)

    q = db.query(Issue).filter(haversine <= radius)
    if category:
        q = q.filter(Issue.category == category)
    if status:
        q = q.filter(Issue.status == status)
    items = q.limit(50).all()

    def dist(i: Issue) -> float:
        import math
        R = 6371000
        dlat = math.radians(lat - i.lat)
        dlng = math.radians(lng - i.lng)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat)) * math.cos(math.radians(i.lat)) * math.sin(dlng / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))

    return {
        "items": [issue_to_summary(i, round(dist(i), 1)) for i in items],
        "total": len(items),
    }


@router.get("/mine", response_model=MyIssuesOut)
def get_my_issues(
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    issues = db.query(Issue).filter(Issue.reporter_id == current_user.id).all()
    open_statuses = {StatusEnum.Reported, StatusEnum.Assigned, StatusEnum.InProgress, StatusEnum.Reopened}
    open_count = sum(1 for i in issues if i.status in open_statuses)
    resolved   = [i for i in issues if i.status == StatusEnum.Resolved]

    avg_days = 0.0
    if resolved:
        def days(i: Issue) -> int:
            r = i.resolved_at.replace(tzinfo=timezone.utc) if i.resolved_at and i.resolved_at.tzinfo is None else i.resolved_at
            c = i.created_at.replace(tzinfo=timezone.utc)  if i.created_at.tzinfo  is None else i.created_at
            return (r - c).days if r else 0
        avg_days = round(sum(days(i) for i in resolved) / len(resolved), 1)

    return MyIssuesOut(
        items=[issue_to_summary(i) for i in issues],
        stats=MyIssueStats(
            total=len(issues),
            open=open_count,
            resolved=len(resolved),
            avg_days=avg_days,
        ),
    )


@router.get("/similar", response_model=dict)
def get_similar(
    lat: float = Query(...),
    lng: float = Query(...),
    category: Optional[str] = None,
    text: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_citizen),
):
    q = db.query(Issue)
    if category:
        q = q.filter(Issue.category == category)
    items = q.limit(5).all()
    return {"items": [issue_to_summary(i) for i in items]}


@router.post("", response_model=IssueDetailOut, status_code=201)
async def create_issue(
    title: str = Form(..., max_length=200),
    description: str = Form(...),
    category: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    address: str = Form(..., max_length=300),
    photos: List[UploadFile] = File(default=[]),
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    """
    Submit a new civic issue (citizen only).
    Accepts 0–3 photos as multipart files.
    Validates content type (jpeg/png/webp) and size (≤ 5 MB) before uploading.
    Returns 502 if Cloudinary is unreachable — issue is NOT created.
    """
    # ── Validate category ──────────────────────────────────────────────────
    try:
        cat_enum = CategoryEnum(category)
    except ValueError:
        valid = [e.value for e in CategoryEnum]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{category}'. Valid values: {valid}",
        )

    # ── Upload photos first — abort early if Cloudinary fails ─────────────
    # upload_many raises 400 (validation) or 502 (Cloudinary error) — no DB
    # rows have been written yet, so nothing to roll back.
    photo_urls = await upload_many(photos, min_count=0, max_count=3)

    # ── Auto-assign team ───────────────────────────────────────────────────
    team_name = CATEGORY_TEAM.get(category)
    team: Optional[Team] = None
    if team_name:
        team = db.query(Team).filter(Team.name == team_name).first()

    # ── Create issue ───────────────────────────────────────────────────────
    ref = make_reference_id(db)
    issue = Issue(
        reference_id=ref,
        title=title,
        description=description,
        category=cat_enum,
        lat=lat,
        lng=lng,
        address=address,
        status=StatusEnum.Reported,
        severity=3,
        affected_count=1,
        priority_score=0.0,
        reporter_id=current_user.id,
        team_id=team.id if team else None,
    )
    db.add(issue)
    db.flush()  # get issue.id without committing

    # ── Attach photos ──────────────────────────────────────────────────────
    for url in photo_urls:
        db.add(IssuePhoto(issue_id=issue.id, url=url, kind=PhotoKindEnum.before))

    # ── First StatusHistory row ────────────────────────────────────────────
    db.add(StatusHistory(
        issue_id=issue.id,
        status=StatusEnum.Reported,
        note="Issue reported via CivicFix.",
        actor_role="citizen",
        changed_by=current_user.id,
    ))

    db.commit()
    db.refresh(issue)
    return issue_to_detail(issue, current_user, db)


@router.get("/{issue_id}", response_model=IssueDetailOut)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get full issue detail: photos, status timeline, team, and priority breakdown.
    Public endpoint — auth is optional (affects has_upvoted / is_owner flags).
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found.")
    return issue_to_detail(issue, current_user, db)


@router.post("/{issue_id}/upvote", response_model=UpvoteOut)
def upvote_issue(
    issue_id: int,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found.")
    existing = db.query(Upvote).filter_by(issue_id=issue_id, user_id=current_user.id).first()
    if existing:
        db.delete(existing)
        issue.affected_count = max(0, issue.affected_count - 1)
        has_upvoted = False
    else:
        db.add(Upvote(issue_id=issue_id, user_id=current_user.id))
        issue.affected_count += 1
        has_upvoted = True
    db.commit()
    return UpvoteOut(affected_count=issue.affected_count, has_upvoted=has_upvoted)


@router.post("/{issue_id}/feedback", response_model=IssueDetailOut)
def issue_feedback(
    issue_id: int,
    payload: FeedbackRequest,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found.")
    if issue.reporter_id != current_user.id:
        raise HTTPException(403, "You can only give feedback on your own issues.")
    if issue.status != StatusEnum.Resolved:
        raise HTTPException(422, "Issue is not resolved yet.")

    if payload.action == "satisfied":
        issue.satisfaction = SatisfactionEnum.satisfied
    elif payload.action == "reopen":
        issue.satisfaction = SatisfactionEnum.reopened
        issue.status = StatusEnum.Reopened
        db.add(StatusHistory(
            issue_id=issue.id,
            status=StatusEnum.Reopened,
            note="Citizen indicated issue persists.",
            actor_role="citizen",
            changed_by=current_user.id,
        ))
    else:
        raise HTTPException(422, "action must be 'satisfied' or 'reopen'.")

    db.commit()
    db.refresh(issue)
    return issue_to_detail(issue, current_user, db)
