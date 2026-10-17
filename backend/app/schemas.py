"""
Pydantic schemas — shaped to match the API contract exactly.
All response models use from_attributes=True so SQLAlchemy models
can be passed directly.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, ConfigDict


# ── Config mixin ─────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str          # min 8 enforced in router


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(OrmBase):
    id:      int
    name:    str
    email:   str
    role:    str
    team_id: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    user:         UserOut


# ── Priority ──────────────────────────────────────────────────────────────────

class PriorityComponents(BaseModel):
    severity:         float
    community_impact: float
    time_unresolved:  float


class PriorityWeights(BaseModel):
    severity:         float = 0.40
    community_impact: float = 0.35
    time_unresolved:  float = 0.25


class PriorityOut(BaseModel):
    score:      float
    label:      str          # Critical / High / Medium / Low
    components: PriorityComponents
    weights:    PriorityWeights = PriorityWeights()


# ── Photo ─────────────────────────────────────────────────────────────────────

class PhotoOut(OrmBase):
    url:  str
    kind: str   # before | after


# ── Timeline ─────────────────────────────────────────────────────────────────

class TimelineItemOut(OrmBase):
    status:     str
    note:       Optional[str]    = None
    photo_url:  Optional[str]    = None
    actor_role: str
    created_at: datetime


# ── Team ─────────────────────────────────────────────────────────────────────

class TeamOut(OrmBase):
    id:   int
    name: str


# ── Issue summary (list views) ────────────────────────────────────────────────

class IssueSummaryOut(BaseModel):
    id:            int
    reference_id:  str
    title:         str
    category:      str
    status:        str
    address:       str
    lat:           float
    lng:           float
    distance_m:    Optional[float] = None
    affected_count: int
    thumbnail:     Optional[str]   = None
    priority:      PriorityOut
    created_at:    datetime


# ── Issue detail (full citizen view) ─────────────────────────────────────────

class IssueDetailOut(IssueSummaryOut):
    description:    str
    photos:         List[PhotoOut]     = []
    team:           Optional[TeamOut]  = None
    parent_issue_id: Optional[int]    = None
    timeline:       List[TimelineItemOut] = []
    satisfaction:   Optional[str]     = None
    resolved_at:    Optional[datetime] = None
    has_upvoted:    bool               = False
    is_owner:       bool               = False


# ── Submit issue ──────────────────────────────────────────────────────────────

class IssueCreateRequest(BaseModel):
    title:       str
    description: str
    category:    str
    lat:         float
    lng:         float
    address:     str
    # photos come as UploadFile list in the router


# ── Upvote ────────────────────────────────────────────────────────────────────

class UpvoteOut(BaseModel):
    affected_count: int
    has_upvoted:    bool


# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    action: str   # "satisfied" | "reopen"


# ── AI photo analysis ─────────────────────────────────────────────────────────

class AnalyzePhotoOut(BaseModel):
    suggested_category: str
    severity:           int    # 1-5
    short_description:  str


# ── Geo reverse ──────────────────────────────────────────────────────────────

class ReverseGeoOut(BaseModel):
    address: str


# ── Track (public, no PII) ────────────────────────────────────────────────────

class TrackStep(BaseModel):
    label: str
    done:  bool


class TrackOut(BaseModel):
    reference_id:    str
    status:          str
    priority_label:  str
    category:        str
    area:            str
    team:            Optional[str] = None
    last_update:     Optional[dict] = None
    days_open:       int
    sla_text:        str
    has_after_photo: bool
    steps:           List[TrackStep]


# ── Public stats ──────────────────────────────────────────────────────────────

class PublicStatsOut(BaseModel):
    total:                int
    resolved:             int
    avg_resolution_days:  float


class RecentResolvedItem(BaseModel):
    reference_id: str
    title:        str
    category:     str
    area:         str
    before_url:   Optional[str] = None
    after_url:    Optional[str] = None
    resolved_at:  datetime


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationOut(OrmBase):
    id:           int
    issue_id:     Optional[int] = None
    reference_id: Optional[str] = None
    message:      str
    is_read:      bool
    created_at:   datetime


class NotificationListOut(BaseModel):
    items:        List[NotificationOut]
    unread_count: int


# ── Bot ───────────────────────────────────────────────────────────────────────

class BotMessageRequest(BaseModel):
    message:  str
    lang:     Optional[str] = "en"
    history:  Optional[List[dict]] = []


class BotLink(BaseModel):
    label: str
    path:  str


class BotMessageOut(BaseModel):
    reply:       str
    intent:      str
    status_card: Optional[dict]   = None
    links:       List[BotLink]    = []
    suggestions: List[str]        = []


# ── Mine (my complaints) ──────────────────────────────────────────────────────

class MyIssueStats(BaseModel):
    total:    int
    open:     int
    resolved: int
    avg_days: float


class MyIssuesOut(BaseModel):
    items: List[IssueSummaryOut]
    stats: MyIssueStats
