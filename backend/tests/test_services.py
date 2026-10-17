"""
tests/test_services.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for:
  - haversine (services/duplicates)
  - duplicate_score — clear duplicate (score ≥ 0.65)
  - duplicate_score — clear non-duplicate (score < 0.65)
  - calculate_priority — all four labels (Critical/High/Medium/Low)

Run with:
    cd backend
    python -m pytest tests/test_services.py -v
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow running from the backend/ directory without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.duplicates import haversine, duplicate_score
from app.services.priority import calculate_priority
from app.models import CategoryEnum, StatusEnum


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_issue(
    *,
    title: str = "Test issue",
    description: str = "No description",
    category: CategoryEnum = CategoryEnum.Pothole,
    status: StatusEnum = StatusEnum.Reported,
    lat: float = 18.5074,
    lng: float = 73.8077,
    severity: int = 3,
    affected_count: int = 0,
    days_ago: float = 0.0,
    duplicates: list | None = None,
) -> MagicMock:
    """Build a lightweight Issue mock suitable for service layer tests."""
    issue              = MagicMock()
    issue.id           = 1
    issue.reference_id = "CF-2026-000001"
    issue.title        = title
    issue.description  = description
    issue.category     = category
    issue.status       = status
    issue.lat          = lat
    issue.lng          = lng
    issue.severity     = severity
    issue.affected_count = affected_count
    issue.duplicates   = duplicates or []
    issue.photos       = []

    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    issue.created_at   = created

    return issue


# ── Haversine tests ───────────────────────────────────────────────────────────

class TestHaversine:
    def test_same_point_is_zero(self):
        """Distance between a point and itself must be 0 m."""
        assert haversine(18.5074, 73.8077, 18.5074, 73.8077) == pytest.approx(0.0, abs=1e-6)

    def test_known_distance_pune(self):
        """
        Nal Stop (18.5074, 73.8077) to FC Road (18.5308, 73.8490).
        Real world distance ≈ 4.95 km — we accept ±150 m tolerance.
        """
        dist = haversine(18.5074, 73.8077, 18.5308, 73.8490)
        assert 4800 < dist < 5100, f"Expected ~4950 m, got {dist:.0f} m"

    def test_very_close_points(self):
        """Two points 50 m apart should measure within ±5 m."""
        # Shift lat by 50 m ≈ 0.00045°
        dist = haversine(18.5074, 73.8077, 18.5074 + 0.00045, 73.8077)
        assert 45 < dist < 55, f"Expected ~50 m, got {dist:.1f} m"

    def test_symmetry(self):
        """haversine(A, B) == haversine(B, A)."""
        d1 = haversine(18.50, 73.80, 18.52, 73.85)
        d2 = haversine(18.52, 73.85, 18.50, 73.80)
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_positive_result(self):
        """Result must always be non-negative."""
        assert haversine(0.0, 0.0, 10.0, 10.0) >= 0


# ── Duplicate score tests ─────────────────────────────────────────────────────

class TestDuplicateScore:
    def test_clear_duplicate_high_score(self):
        """
        Two Pothole issues 30 m apart with very similar text → score ≥ 0.65.
        """
        text = "Deep pothole on Karve Road near Nal Stop bus stand dangerous"
        new  = _make_issue(
            title="Deep pothole on Karve Road near Nal Stop",
            description="Large dangerous pothole blocking traffic",
            category=CategoryEnum.Pothole,
            lat=18.5074, lng=73.8077,
        )
        existing = _make_issue(
            title="Pothole on Karve Road near Nal Stop bus stand",
            description="Deep pothole near Nal Stop — very dangerous for bikes",
            category=CategoryEnum.Pothole,
            lat=18.5074 + 0.00027,  # ≈ 30 m north
            lng=73.8077,
        )
        score = duplicate_score(new, existing)
        assert score >= 0.65, (
            f"Expected clear duplicate score ≥ 0.65, got {score:.4f}"
        )

    def test_clear_non_duplicate_low_score(self):
        """
        Different category, 800 m apart, completely different text → score < 0.65.
        """
        new = _make_issue(
            title="Deep pothole on Karve Road",
            description="Large pothole blocking traffic lane",
            category=CategoryEnum.Pothole,
            lat=18.5074, lng=73.8077,
        )
        far_garbage = _make_issue(
            title="Garbage dump near Baner lake embankment",
            description="Illegal waste dumping polluting the water body",
            category=CategoryEnum.Garbage,
            lat=18.5600, lng=73.7850,   # ≈ 8 km away
        )
        score = duplicate_score(new, far_garbage)
        assert score < 0.65, (
            f"Expected non-duplicate score < 0.65, got {score:.4f}"
        )

    def test_same_location_different_category(self):
        """Same coordinates but different category — category mismatch penalises."""
        pothole  = _make_issue(category=CategoryEnum.Pothole, lat=18.52, lng=73.84)
        garbage  = _make_issue(category=CategoryEnum.Garbage, lat=18.52, lng=73.84,
                               title="Garbage near road", description="Waste on road")
        score    = duplicate_score(pothole, garbage)
        # distance_score=1.0, same_category=0, text_similarity≈ small
        # 0.5*1.0 + 0.2*0 + 0.3*sim < 0.65 for very different text
        assert score < 0.65

    def test_score_range(self):
        """Score must always be in [0, 1]."""
        a = _make_issue(lat=0.0, lng=0.0)
        b = _make_issue(lat=90.0, lng=180.0)
        s = duplicate_score(a, b)
        assert 0.0 <= s <= 1.0


# ── Priority label tests ──────────────────────────────────────────────────────

class TestPriorityLabels:
    """Verify the four priority labels are assigned at the correct thresholds."""

    def _priority(self, issue):
        return calculate_priority(issue)

    def test_critical_label(self):
        """
        Water Leak, severity 5, 30 votes + 5 duplicate children, 10 days open
        (SLA=2d → well past SLA → high time score).
        Expected score ≥ 75 → Critical.
        """
        issue = _make_issue(
            title="Burst water main flooding the hospital area — dangerous accident zone",
            description="Flooding near hospital, dangerous for residents",
            category=CategoryEnum.WaterLeak,
            severity=5,
            affected_count=30,
            duplicates=[MagicMock()] * 5,
            days_ago=10,  # SLA=2d → 8 days past SLA → time_score capped at 100
        )
        result = self._priority(issue)
        assert result.label == "Critical", (
            f"Expected Critical, got {result.label} (score={result.score})"
        )
        assert result.score >= 75

    def test_high_label(self):
        """
        Pothole, severity 4, 10 votes, 8 days open (SLA=7d → slightly past).
        Expected score ≥ 55 and < 75 → High.
        """
        issue = _make_issue(
            category=CategoryEnum.Pothole,
            severity=4,
            affected_count=10,
            duplicates=[],
            days_ago=8,
        )
        result = self._priority(issue)
        assert result.label == "High", (
            f"Expected High, got {result.label} (score={result.score})"
        )
        assert 55 <= result.score < 75

    def test_medium_label(self):
        """
        Garbage, severity 3, 8 votes, 2 days open (SLA=3d → within SLA).
        severity_score ≈ (3/5)*50 = 30, ci_score = 8*5=40, time = (2/3)*100≈66.7
        score ≈ 30*0.4 + 40*0.35 + 66.7*0.25 ≈ 12 + 14 + 16.7 = 42.7 → Medium
        """
        issue = _make_issue(
            category=CategoryEnum.Garbage,
            severity=3,
            affected_count=8,
            duplicates=[],
            days_ago=2,
        )
        result = self._priority(issue)
        assert result.label == "Medium", (
            f"Expected Medium, got {result.label} (score={result.score})"
        )
        assert 35 <= result.score < 55

    def test_low_label(self):
        """
        Other, severity 1, 0 votes, just created (0 days).
        severity_score ≈ (1/5)*45 = 9, ci=0, time=0
        score ≈ 9*0.4 = 3.6 → Low
        """
        issue = _make_issue(
            category=CategoryEnum.Other,
            severity=1,
            affected_count=0,
            duplicates=[],
            days_ago=0,
        )
        result = self._priority(issue)
        assert result.label == "Low", (
            f"Expected Low, got {result.label} (score={result.score})"
        )
        assert result.score < 35

    def test_components_sum_approximately(self):
        """Weighted sum of components ≈ total score (within rounding tolerance)."""
        issue = _make_issue(
            category=CategoryEnum.Pothole,
            severity=3,
            affected_count=5,
            duplicates=[],
            days_ago=4,
        )
        result = self._priority(issue)
        expected = (
            result.components.severity         * 0.40
            + result.components.community_impact * 0.35
            + result.components.time_unresolved  * 0.25
        )
        assert abs(result.score - round(expected, 1)) < 0.2

    def test_keyword_boost_raises_score(self):
        """Adding danger keywords to title increases the severity component."""
        base = _make_issue(
            title="Pothole on road",
            description="Small pothole",
            category=CategoryEnum.Pothole,
            severity=3, affected_count=0, duplicates=[], days_ago=1,
        )
        boosted = _make_issue(
            title="Dangerous pothole near school causing accidents",
            description="Flooding risk near hospital — urgent",
            category=CategoryEnum.Pothole,
            severity=3, affected_count=0, duplicates=[], days_ago=1,
        )
        r_base    = self._priority(base)
        r_boosted = self._priority(boosted)
        assert r_boosted.components.severity > r_base.components.severity, (
            "Keyword boost should increase severity component"
        )
