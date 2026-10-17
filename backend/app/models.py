from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Integer, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# ── Enums ────────────────────────────────────────────────────────────────────

import enum


class RoleEnum(str, enum.Enum):
    citizen = "citizen"
    worker  = "worker"
    admin   = "admin"


class StatusEnum(str, enum.Enum):
    Reported    = "Reported"
    Assigned    = "Assigned"
    InProgress  = "In Progress"
    Resolved    = "Resolved"
    Reopened    = "Reopened"


class CategoryEnum(str, enum.Enum):
    Pothole     = "Pothole"
    WaterLeak   = "Water Leak"
    Garbage     = "Garbage"
    Streetlight = "Streetlight"
    Other       = "Other"


class PhotoKindEnum(str, enum.Enum):
    before = "before"
    after  = "after"


class SatisfactionEnum(str, enum.Enum):
    satisfied = "satisfied"
    reopened  = "reopened"


# ── Helper ───────────────────────────────────────────────────────────────────

def utcnow():
    return datetime.now(timezone.utc)


# ── Models ───────────────────────────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False, unique=True)
    # Comma-separated category names e.g. "Pothole,Other"
    categories = Column(String(255), nullable=False, default="")

    members = relationship("User",  back_populates="team")
    issues  = relationship("Issue", back_populates="team")


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(150), nullable=False)
    email        = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role         = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.citizen)
    team_id      = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at   = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    team          = relationship("Team",         back_populates="members")
    reported      = relationship("Issue",        back_populates="reporter",   foreign_keys="Issue.reporter_id")
    upvotes       = relationship("Upvote",       back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    status_changes = relationship("StatusHistory", back_populates="changed_by_user")


class Issue(Base):
    __tablename__ = "issues"

    id               = Column(Integer, primary_key=True, index=True)
    # CF-2026-000001  — set by the service layer before insert
    reference_id     = Column(String(20), unique=True, index=True, nullable=False)

    title            = Column(String(200), nullable=False)
    description      = Column(Text, nullable=False)
    category         = Column(Enum(CategoryEnum), nullable=False)
    address          = Column(String(300), nullable=False)
    lat              = Column(Float, nullable=False)
    lng              = Column(Float, nullable=False)

    status           = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.Reported)
    severity         = Column(Integer, nullable=False, default=3)          # 1-5 (AI or user)
    community_impact = Column(Integer, nullable=False, default=0)          # raw upvote count
    priority_score   = Column(Float,   nullable=False, default=0.0)        # 0-100
    affected_count   = Column(Integer, nullable=False, default=0)

    # Duplicate detection
    parent_issue_id  = Column(Integer, ForeignKey("issues.id"), nullable=True)
    duplicate_score  = Column(Float, nullable=True)

    team_id          = Column(Integer, ForeignKey("teams.id"),  nullable=True)
    reporter_id      = Column(Integer, ForeignKey("users.id"),  nullable=False)

    satisfaction     = Column(Enum(SatisfactionEnum), nullable=True)
    created_at       = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at      = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reporter    = relationship("User",          back_populates="reported", foreign_keys=[reporter_id])
    team        = relationship("Team",          back_populates="issues")
    photos      = relationship("IssuePhoto",    back_populates="issue",   cascade="all, delete-orphan")
    timeline    = relationship("StatusHistory", back_populates="issue",   cascade="all, delete-orphan",
                               order_by="StatusHistory.created_at")
    upvotes     = relationship("Upvote",        back_populates="issue",   cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="issue",  cascade="all, delete-orphan")
    duplicates  = relationship("Issue", foreign_keys=[parent_issue_id])

    __table_args__ = (
        Index("ix_issues_lat_lng", "lat", "lng"),
        Index("ix_issues_status",  "status"),
        Index("ix_issues_category","category"),
    )


class IssuePhoto(Base):
    __tablename__ = "issue_photos"

    id         = Column(Integer, primary_key=True, index=True)
    issue_id   = Column(Integer, ForeignKey("issues.id"), nullable=False)
    url        = Column(String(500), nullable=False)
    kind       = Column(Enum(PhotoKindEnum), nullable=False, default=PhotoKindEnum.before)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    issue = relationship("Issue", back_populates="photos")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id            = Column(Integer, primary_key=True, index=True)
    issue_id      = Column(Integer, ForeignKey("issues.id"), nullable=False)
    status        = Column(Enum(StatusEnum), nullable=False)
    note          = Column(Text, nullable=True)
    photo_url     = Column(String(500), nullable=True)
    actor_role    = Column(String(20),  nullable=False, default="system")
    changed_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    issue          = relationship("Issue", back_populates="timeline")
    changed_by_user = relationship("User", back_populates="status_changes")


class Upvote(Base):
    __tablename__ = "upvotes"

    id       = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    user_id  = Column(Integer, ForeignKey("users.id"),  nullable=False)

    issue = relationship("Issue", back_populates="upvotes")
    user  = relationship("User",  back_populates="upvotes")

    __table_args__ = (
        UniqueConstraint("issue_id", "user_id", name="uq_upvote_issue_user"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"),  nullable=False)
    issue_id   = Column(Integer, ForeignKey("issues.id"), nullable=True)
    message    = Column(Text, nullable=False)
    is_read    = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user  = relationship("User",  back_populates="notifications")
    issue = relationship("Issue", back_populates="notifications")
