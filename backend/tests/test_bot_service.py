"""
tests/test_bot_service.py
────────────────────────────────────────────────────────────────────────────
Unit tests for:
  - services/bot.py   (parse_reference_id, build_status_payload,
                        phrase_with_gemini)
  - routers/track.py  (rate limiter via _check_rate_limit)

Scenarios covered:
  ✓  Valid canonical reference ID found and returned
  ✓  Lowercase + no-dash ID normalised correctly
  ✓  ID with spaces tolerated
  ✓  Unknown / missing ID returns None
  ✓  build_status_payload never includes PII fields
  ✓  phrase_with_gemini falls back to template when Gemini is disabled
  ✓  phrase_with_gemini falls back to template on timeout
  ✓  phrase_with_gemini falls back to template on HTTP error
  ✓  Template fallback returns Hindi when lang="hi"
  ✓  21st request from same IP raises HTTP 429

Run with:
    cd backend
    python -m pytest tests/test_bot_service.py -v
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bot import (
    build_status_payload,
    parse_reference_id,
    phrase_with_gemini,
    _template_reply,
    SLA_DAYS,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


def _make_issue(
    *,
    reference_id: str = "CF-2026-000042",
    title: str = "Big pothole",
    description: str = "Very deep",
    category_value: str = "Pothole",
    status_value: str = "Assigned",
    address: str = "Nal Stop, Karve Road, Pune",
    lat: float = 18.5074,
    lng: float = 73.8077,
    severity: int = 3,
    affected_count: int = 5,
    days_ago: float = 2.0,
    team_name: str | None = "Roads",
    reporter_name: str = "Jane Doe",
    reporter_email: str = "jane@example.com",
    has_after_photo: bool = False,
    timeline_notes: list[str] | None = None,
) -> MagicMock:
    """Build a lightweight Issue mock for service-layer tests."""
    issue = MagicMock()
    issue.reference_id = reference_id
    issue.title        = title
    issue.description  = description
    issue.address      = address
    issue.lat          = lat
    issue.lng          = lng
    issue.severity     = severity
    issue.affected_count = affected_count
    issue.priority_score = 0.0    # internal — must not leak

    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    issue.created_at = created
    issue.resolved_at = None

    # Category enum mock
    issue.category = MagicMock()
    issue.category.value = category_value

    # Status enum mock
    issue.status = MagicMock()
    issue.status.value = status_value

    # Team (or None)
    if team_name:
        issue.team = MagicMock()
        issue.team.name = team_name
    else:
        issue.team = None

    # Reporter (PII — must NOT appear in payload)
    issue.reporter = MagicMock()
    issue.reporter.name  = reporter_name
    issue.reporter.email = reporter_email
    issue.reporter_id    = 99

    # Photos
    def _photo(kind: str) -> MagicMock:
        p = MagicMock()
        p.kind = MagicMock()
        p.kind.value = kind
        return p

    issue.photos = [_photo("before")]
    if has_after_photo:
        issue.photos.append(_photo("after"))

    # Timeline
    if timeline_notes is None:
        timeline_notes = ["Issue reported via CivicFix."]

    tl_entries = []
    for note in timeline_notes:
        entry = MagicMock()
        entry.note = note
        entry.actor_role = "citizen"
        entry.created_at = created + timedelta(hours=1)
        tl_entries.append(entry)
    issue.timeline = tl_entries

    issue.duplicates = []
    return issue


# Patch target for httpx.AsyncClient inside bot service
_ASYNC_CLIENT = "app.services.bot.httpx.AsyncClient"
_SETTINGS     = "app.services.bot.settings"


def _gemini_ok_response(text: str) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": text}]}}]
    }
    return resp


def _mock_client(response: MagicMock) -> MagicMock:
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__  = AsyncMock(return_value=False)
    return cm


# ─────────────────────────────────────────────────────────────────────────────
# parse_reference_id
# ─────────────────────────────────────────────────────────────────────────────

class TestParseReferenceId:
    """CF-YYYY-NNNNNN extraction with tolerant normalisation."""

    def test_canonical_format(self):
        assert parse_reference_id("CF-2026-000001") == "CF-2026-000001"

    def test_canonical_in_sentence(self):
        assert parse_reference_id("my complaint CF-2026-000042 is late") == "CF-2026-000042"

    def test_lowercase_no_dashes(self):
        """cf2026000001  →  CF-2026-000001"""
        assert parse_reference_id("cf2026000001") == "CF-2026-000001"

    def test_lowercase_with_dashes(self):
        assert parse_reference_id("cf-2026-000099") == "CF-2026-000099"

    def test_spaces_between_parts(self):
        assert parse_reference_id("CF 2026 000007") == "CF-2026-000007"

    def test_mixed_case_with_spaces(self):
        assert parse_reference_id("Cf 2026 000099 is my ID") == "CF-2026-000099"

    def test_no_id_returns_none(self):
        assert parse_reference_id("Hello, I have a pothole near my house") is None

    def test_partial_id_returns_none(self):
        # Only 4 digits after CF — not a valid serial (need 10 total)
        assert parse_reference_id("CF-2026") is None

    def test_unrelated_numbers_ignored(self):
        assert parse_reference_id("I paid 2026 rupees today") is None

    def test_multiple_ids_returns_first(self):
        result = parse_reference_id("CF-2026-000001 and CF-2026-000002")
        assert result == "CF-2026-000001"

    def test_returns_canonical_uppercase(self):
        result = parse_reference_id("cf-2026-000005")
        assert result == result.upper()


# ─────────────────────────────────────────────────────────────────────────────
# build_status_payload — PII and field checks
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildStatusPayload:
    """Verify that payload never leaks PII and always has required keys."""

    REQUIRED_KEYS = {
        "reference_id", "status", "priority_label", "category",
        "area", "team", "last_update", "days_open",
        "sla_remaining_or_overdue", "has_after_photo",
    }
    FORBIDDEN_KEYS = {
        "reporter_id", "reporter", "email", "lat", "lng",
        "priority_score", "duplicate_score", "phone",
    }

    def test_required_keys_present(self):
        issue = _make_issue()
        p = build_status_payload(issue)
        missing = self.REQUIRED_KEYS - p.keys()
        assert not missing, f"Missing keys: {missing}"

    def test_no_pii_keys(self):
        """Payload must not contain any PII or internal field names."""
        issue = _make_issue(reporter_name="Jane Doe", reporter_email="jane@example.com")
        p = build_status_payload(issue)
        for key in self.FORBIDDEN_KEYS:
            assert key not in p, f"PII key '{key}' found in payload"

    def test_no_exact_coordinates(self):
        """lat / lng values must not appear in the serialised payload."""
        issue = _make_issue(lat=18.5074, lng=73.8077)
        p = build_status_payload(issue)
        payload_str = str(p)
        assert "18.5074" not in payload_str, "Exact lat leaked"
        assert "73.8077" not in payload_str, "Exact lng leaked"

    def test_reporter_name_not_in_values(self):
        issue = _make_issue(reporter_name="SuperSecretReporter")
        p = build_status_payload(issue)
        assert "SuperSecretReporter" not in str(p)

    def test_area_is_locality_not_full_address(self):
        issue = _make_issue(address="Nal Stop, Karve Road, Kothrud, Pune 411038")
        p = build_status_payload(issue)
        # area should be only the first segment
        assert p["area"] == "Nal Stop"
        # full address must NOT appear
        assert "Karve Road" not in p["area"]

    def test_team_name_returned_correctly(self):
        issue = _make_issue(team_name="Roads")
        assert build_status_payload(issue)["team"] == "Roads"

    def test_no_team_returns_none(self):
        issue = _make_issue(team_name=None)
        assert build_status_payload(issue)["team"] is None

    def test_has_after_photo_false(self):
        issue = _make_issue(has_after_photo=False)
        assert build_status_payload(issue)["has_after_photo"] is False

    def test_has_after_photo_true(self):
        issue = _make_issue(has_after_photo=True)
        assert build_status_payload(issue)["has_after_photo"] is True

    def test_days_open_non_negative(self):
        issue = _make_issue(days_ago=0.0)
        assert build_status_payload(issue)["days_open"] >= 0

    def test_sla_overdue_text(self):
        # Pothole SLA = 7 days, 10 days open → overdue by 3
        issue = _make_issue(category_value="Pothole", days_ago=10,
                            status_value="Reported")
        p = build_status_payload(issue)
        assert "Overdue" in p["sla_remaining_or_overdue"]

    def test_sla_remaining_text(self):
        # Pothole SLA = 7 days, 2 days open → 5 remaining
        issue = _make_issue(category_value="Pothole", days_ago=2,
                            status_value="Reported")
        p = build_status_payload(issue)
        assert "remaining" in p["sla_remaining_or_overdue"]

    def test_sla_resolved_text(self):
        issue = _make_issue(status_value="Resolved")
        p = build_status_payload(issue)
        assert "Resolved" in p["sla_remaining_or_overdue"]

    def test_last_update_note_present(self):
        issue = _make_issue(timeline_notes=["Assigned to Roads team."])
        p = build_status_payload(issue)
        assert p["last_update"]["note"] == "Assigned to Roads team."

    def test_last_update_none_when_no_timeline(self):
        issue = _make_issue(timeline_notes=[])
        p = build_status_payload(issue)
        assert p["last_update"] is None

    def test_priority_label_valid(self):
        issue = _make_issue()
        label = build_status_payload(issue)["priority_label"]
        assert label in {"Critical", "High", "Medium", "Low"}


# ─────────────────────────────────────────────────────────────────────────────
# phrase_with_gemini — fallback tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPhraseWithGemini:
    """phrase_with_gemini never raises; falls back to template on any failure."""

    def _payload(self) -> dict:
        issue = _make_issue()
        return build_status_payload(issue)

    # ── Gemini disabled ───────────────────────────────────────────────────────

    def test_no_api_key_returns_template(self):
        p = self._payload()
        result = run(phrase_with_gemini(p, "en", api_key=""))
        assert isinstance(result, str)
        assert len(result) > 10
        # Template should mention the reference_id
        assert p["reference_id"] in result

    def test_whitespace_api_key_returns_template(self):
        result = run(phrase_with_gemini(self._payload(), "en", api_key="   "))
        assert self._payload()["reference_id"] in result

    # ── Network failures ──────────────────────────────────────────────────────

    def test_timeout_returns_template(self):
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timed out")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(phrase_with_gemini(self._payload(), "en", api_key="fake-key"))
        assert isinstance(result, str)
        assert len(result) > 5

    def test_connect_error_returns_template(self):
        client = AsyncMock()
        client.post.side_effect = httpx.ConnectError("no network")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(phrase_with_gemini(self._payload(), "en", api_key="fake-key"))
        assert isinstance(result, str)

    def test_http_401_returns_template(self):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 401
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=resp
        )
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(phrase_with_gemini(self._payload(), "en", api_key="bad-key"))
        assert isinstance(result, str)

    def test_http_503_returns_template(self):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 503
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=resp
        )
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(phrase_with_gemini(self._payload(), "hi", api_key="fake-key"))
        assert isinstance(result, str)

    def test_unexpected_exception_returns_template(self):
        client = AsyncMock()
        client.post.side_effect = RuntimeError("unexpected")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(phrase_with_gemini(self._payload(), "en", api_key="fake-key"))
        assert isinstance(result, str)

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_gemini_reply_returned_on_success(self):
        resp = _gemini_ok_response("Your complaint CF-2026-000042 is being processed.")
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(phrase_with_gemini(self._payload(), "en", api_key="valid-key"))
        assert "CF-2026-000042" in result

    # ── Language templates ────────────────────────────────────────────────────

    def test_template_english_contains_reference_id(self):
        p = self._payload()
        r = _template_reply(p, "en")
        assert p["reference_id"] in r

    def test_template_hindi_contains_reference_id(self):
        p = self._payload()
        r = _template_reply(p, "hi")
        assert p["reference_id"] in r

    def test_template_hindi_triggered_for_hi_lang(self):
        """Template in Hindi should contain Devanagari characters."""
        p = self._payload()
        r = _template_reply(p, "hi")
        # Check for at least one Devanagari character (U+0900–U+097F)
        has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in r)
        assert has_devanagari, f"Expected Devanagari in Hindi reply: {r!r}"

    def test_template_hindi_triggered_for_hi_IN(self):
        p = self._payload()
        r = _template_reply(p, "hi-IN")
        has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in r)
        assert has_devanagari


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiter — _check_rate_limit
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimiter:
    """21st request from the same IP within 60 s must raise HTTP 429."""

    def setup_method(self):
        """Clear the in-memory counter between tests."""
        from app.routers.track import _counters
        _counters.clear()

    def test_first_20_requests_succeed(self):
        from app.routers.track import _check_rate_limit
        from fastapi import HTTPException

        ip = "10.0.0.1"
        for i in range(20):
            # Should not raise
            _check_rate_limit(ip)

    def test_21st_request_raises_429(self):
        from app.routers.track import _check_rate_limit
        from fastapi import HTTPException

        ip = "10.0.0.2"
        for _ in range(20):
            _check_rate_limit(ip)

        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(ip)

        assert exc_info.value.status_code == 429

    def test_429_detail_is_friendly(self):
        """The error message must be human-readable, not a raw code."""
        from app.routers.track import _check_rate_limit
        from fastapi import HTTPException

        ip = "10.0.0.3"
        for _ in range(20):
            _check_rate_limit(ip)

        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(ip)

        detail = exc_info.value.detail
        assert isinstance(detail, str)
        assert len(detail) > 20
        # Should NOT be a bare numeric code
        assert detail != "429"
        assert "request" in detail.lower() or "limit" in detail.lower()

    def test_different_ips_are_independent(self):
        """IP A hitting the limit does not affect IP B."""
        from app.routers.track import _check_rate_limit
        from fastapi import HTTPException

        ip_a = "10.0.1.1"
        ip_b = "10.0.1.2"

        for _ in range(20):
            _check_rate_limit(ip_a)

        with pytest.raises(HTTPException):
            _check_rate_limit(ip_a)   # A is blocked

        # B should still be fine after 1 call
        _check_rate_limit(ip_b)   # should not raise

    def test_window_expiry_resets_counter(self):
        """After the 60 s window expires, the counter resets."""
        from app.routers.track import _check_rate_limit, _counters, _WINDOW_SECS
        from fastapi import HTTPException

        ip = "10.0.2.1"
        # Manually inject 20 timestamps that are > 60 s ago
        old_time = time.monotonic() - (_WINDOW_SECS + 5)
        _counters[ip] = [old_time] * 20

        # First request in new window should succeed
        _check_rate_limit(ip)   # should not raise


# ─────────────────────────────────────────────────────────────────────────────
# No-PII regression: payload string must not contain sensitive data
# ─────────────────────────────────────────────────────────────────────────────

class TestNoPIIRegression:
    """End-to-end check: build_status_payload never exposes PII."""

    def test_email_not_in_payload_string(self):
        issue = _make_issue(reporter_email="secret@civicfix.in")
        p = build_status_payload(issue)
        assert "secret@civicfix.in" not in str(p)

    def test_reporter_name_not_in_payload_string(self):
        issue = _make_issue(reporter_name="PrivateCitizen")
        p = build_status_payload(issue)
        assert "PrivateCitizen" not in str(p)

    def test_lat_not_in_payload_string(self):
        issue = _make_issue(lat=12.3456789)
        p = build_status_payload(issue)
        assert "12.3456789" not in str(p)

    def test_lng_not_in_payload_string(self):
        issue = _make_issue(lng=77.9876543)
        p = build_status_payload(issue)
        assert "77.9876543" not in str(p)

    def test_priority_score_not_in_payload(self):
        issue = _make_issue()
        issue.priority_score = 87.654
        p = build_status_payload(issue)
        assert "priority_score" not in p
        assert "87.654" not in str(p)
