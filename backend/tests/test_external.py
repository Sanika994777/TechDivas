"""
tests/test_external.py
────────────────────────────────────────────────────────────────────────────
Unit tests for services/external.py.

Tests are grouped in three classes:
  TestAnalyzePhotoFallback  — every path that should return a safe fallback
  TestAnalyzePhotoSuccess   — happy-path Gemini parsing
  TestReverseGeocodeFallback — every path that should return "lat, lng"
  TestReverseGeocodeSuccess  — happy-path Nominatim parsing

All tests are synchronous — async coroutines are driven with asyncio.run().
No real network calls are ever made; httpx is fully mocked via unittest.mock.

Run with:
    cd backend
    python -m pytest tests/test_external.py -v
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import external as ext
from app.services.external import (
    VALID_CATEGORIES,
    _keyword_fallback,
    _parse_gemini_response,
    analyze_photo,
    reverse_geocode,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    """Drive an async coroutine synchronously."""
    return asyncio.run(coro)


def _gemini_ok_response(category="Pothole", severity=4,
                        description="Large pothole on road.") -> MagicMock:
    """Build a mock httpx.Response that looks like a successful Gemini reply."""
    payload = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "suggested_category": category,
                        "severity": severity,
                        "short_description": description,
                    })
                }]
            }
        }]
    }
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()   # does nothing — no error
    resp.status_code = 200
    return resp


def _nominatim_ok_response(display_name="Karve Road, Pune") -> MagicMock:
    """Build a mock httpx.Response that looks like a successful Nominatim reply."""
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = {"display_name": display_name}
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    return resp


def _error_response(status_code=502) -> MagicMock:
    """Build a mock httpx.Response that raises on raise_for_status."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=resp
    )
    return resp


# Patch target for httpx.AsyncClient used inside external.py
_ASYNC_CLIENT = "app.services.external.httpx.AsyncClient"
# Patch target for settings inside external.py
_SETTINGS = "app.services.external.settings"


def _mock_client(response: MagicMock) -> MagicMock:
    """
    Return a context-manager mock that yields an AsyncClient whose
    post() / get() returns the given response.
    """
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.get  = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__  = AsyncMock(return_value=False)
    return cm


# ── Keyword fallback unit tests ───────────────────────────────────────────────

class TestKeywordFallback:
    def test_pothole_keyword(self):
        r = _keyword_fallback("Big pothole on Karve Road", "")
        assert r["suggested_category"] == "Pothole"

    def test_water_leak_keyword(self):
        r = _keyword_fallback("", "burst pipe flooding the street")
        assert r["suggested_category"] == "Water Leak"
        assert r["severity"] >= 3   # water leaks default to 4

    def test_garbage_keyword(self):
        r = _keyword_fallback("Garbage dump near park", "")
        assert r["suggested_category"] == "Garbage"

    def test_streetlight_keyword(self):
        r = _keyword_fallback("Broken streetlight on highway", "")
        assert r["suggested_category"] == "Streetlight"

    def test_no_match_returns_other(self):
        r = _keyword_fallback("Unknown problem", "Cannot describe")
        assert r["suggested_category"] == "Other"
        assert r["severity"] == 3

    def test_description_checked_too(self):
        r = _keyword_fallback("Some title", "There is a pothole here")
        assert r["suggested_category"] == "Pothole"


# ── Gemini response parser tests ──────────────────────────────────────────────

class TestParseGeminiResponse:
    def test_valid_json_parsed(self):
        raw = '{"suggested_category": "Garbage", "severity": 2, "short_description": "Waste."}'
        result = _parse_gemini_response(raw)
        assert result is not None
        assert result["suggested_category"] == "Garbage"
        assert result["severity"] == 2

    def test_json_embedded_in_text_parsed(self):
        raw = 'Here is the answer:\n{"suggested_category":"Pothole","severity":3,"short_description":"hole"}'
        result = _parse_gemini_response(raw)
        assert result is not None
        assert result["suggested_category"] == "Pothole"

    def test_invalid_category_replaced_with_other(self):
        raw = '{"suggested_category": "Flood", "severity": 3, "short_description": "wet"}'
        result = _parse_gemini_response(raw)
        assert result["suggested_category"] == "Other"

    def test_severity_clamped_to_1_5(self):
        raw = '{"suggested_category": "Pothole", "severity": 99, "short_description": "x"}'
        result = _parse_gemini_response(raw)
        assert result["severity"] == 5

        raw2 = '{"suggested_category": "Pothole", "severity": -3, "short_description": "x"}'
        result2 = _parse_gemini_response(raw2)
        assert result2["severity"] == 1

    def test_no_json_returns_none(self):
        assert _parse_gemini_response("No JSON here at all.") is None

    def test_broken_json_returns_none(self):
        assert _parse_gemini_response("{broken json}") is None

    def test_short_description_truncated(self):
        long_desc = "A" * 200
        raw = json.dumps({
            "suggested_category": "Pothole",
            "severity": 3,
            "short_description": long_desc,
        })
        result = _parse_gemini_response(raw)
        assert len(result["short_description"]) <= 100


# ── analyze_photo: fallback scenarios ────────────────────────────────────────

class TestAnalyzePhotoFallback:
    """
    Each test proves that analyze_photo returns a valid dict (never raises)
    even when the network / API is completely broken.
    """
    _FAKE_KEY = "test-key-123"
    _IMG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"   # invalid but non-empty bytes

    def _fake_settings(self):
        s = MagicMock()
        s.GEMINI_API_KEY = self._FAKE_KEY
        return s

    def _assert_valid(self, result: dict):
        assert result["suggested_category"] in VALID_CATEGORIES
        assert 1 <= result["severity"] <= 5
        assert isinstance(result["short_description"], str)
        assert len(result["short_description"]) > 0

    # ── no API key ────────────────────────────────────────────────────────────

    def test_no_api_key_falls_back(self):
        """Missing GEMINI_API_KEY → keyword fallback, no network call."""
        s = MagicMock(); s.GEMINI_API_KEY = ""
        with patch(_SETTINGS, s):
            result = run(analyze_photo(self._IMG, title="pothole road", description=""))
        self._assert_valid(result)
        assert result["suggested_category"] == "Pothole"  # keyword matched

    def test_empty_api_key_falls_back(self):
        s = MagicMock(); s.GEMINI_API_KEY = "   "   # whitespace only
        with patch(_SETTINGS, s):
            result = run(analyze_photo(self._IMG))
        self._assert_valid(result)
        assert result["suggested_category"] == "Other"

    # ── network / timeout failures ────────────────────────────────────────────

    def test_timeout_falls_back(self):
        """httpx.TimeoutException → keyword/sentinel fallback."""
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timeout")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=cm):
            result = run(analyze_photo(self._IMG, title="leak in pipe", description=""))
        self._assert_valid(result)
        # title contains "leak" → Water Leak via keyword rule
        assert result["suggested_category"] == "Water Leak"

    def test_connection_error_falls_back(self):
        """httpx.ConnectError (network unplugged) → fallback."""
        client = AsyncMock()
        client.post.side_effect = httpx.ConnectError("no route to host")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=cm):
            result = run(analyze_photo(self._IMG))
        self._assert_valid(result)

    def test_http_error_falls_back(self):
        """Non-2xx HTTP (e.g. 401 Unauthorized) → fallback."""
        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=_mock_client(_error_response(401))):
            result = run(analyze_photo(self._IMG, title="garbage dump"))
        self._assert_valid(result)
        assert result["suggested_category"] == "Garbage"

    def test_503_falls_back(self):
        """503 Service Unavailable → fallback."""
        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=_mock_client(_error_response(503))):
            result = run(analyze_photo(self._IMG))
        self._assert_valid(result)

    def test_bad_json_in_response_falls_back(self):
        """Gemini returns 200 but with garbled JSON → fallback."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "I cannot classify this."}]}}]
        }

        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(analyze_photo(self._IMG, title="streetlight broken"))
        self._assert_valid(result)
        assert result["suggested_category"] == "Streetlight"

    def test_unexpected_exception_falls_back(self):
        """Any unexpected exception (e.g. OSError) never propagates."""
        client = AsyncMock()
        client.post.side_effect = OSError("disk full")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=cm):
            result = run(analyze_photo(self._IMG))
        self._assert_valid(result)

    def test_sentinel_fallback_category_is_valid(self):
        """The final sentinel fallback must pass schema validation."""
        s = MagicMock(); s.GEMINI_API_KEY = ""
        with patch(_SETTINGS, s):
            result = run(analyze_photo(self._IMG, title="", description=""))
        assert result["suggested_category"] in VALID_CATEGORIES
        assert result["suggested_category"] == "Other"
        assert result["severity"] == 3


# ── analyze_photo: happy path ─────────────────────────────────────────────────

class TestAnalyzePhotoSuccess:
    _FAKE_KEY = "test-key-ok"
    _IMG = b"\xff\xd8\xff\xe0fake"

    def _fake_settings(self):
        s = MagicMock(); s.GEMINI_API_KEY = self._FAKE_KEY
        return s

    def test_valid_gemini_response_parsed(self):
        resp = _gemini_ok_response("Water Leak", 5, "Burst main flooding road.")
        with patch(_SETTINGS, self._fake_settings()), \
             patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(analyze_photo(self._IMG))
        assert result["suggested_category"] == "Water Leak"
        assert result["severity"] == 5
        assert "Burst" in result["short_description"]

    def test_all_valid_categories_accepted(self):
        for cat in VALID_CATEGORIES:
            resp = _gemini_ok_response(cat, 3, "test")
            with patch(_SETTINGS, self._fake_settings()), \
                 patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
                result = run(analyze_photo(self._IMG))
            assert result["suggested_category"] == cat


# ── reverse_geocode: fallback scenarios ───────────────────────────────────────

class TestReverseGeocodeFallback:
    """
    Prove that reverse_geocode returns {"address": "lat, lng"} (never raises)
    when Nominatim is unreachable or misbehaves.
    """
    _LAT, _LNG = 18.5074, 73.8077
    _FALLBACK = f"{_LAT}, {_LNG}"

    def _assert_fallback(self, result: dict):
        assert result == {"address": self._FALLBACK}

    def test_timeout_returns_coordinate_string(self):
        """TimeoutException → coordinate fallback."""
        client = AsyncMock()
        client.get.side_effect = httpx.TimeoutException("timed out")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        # Reset the rate-limiter so we don't wait 1 s in tests
        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_connect_error_returns_coordinate_string(self):
        """Network unplugged → coordinate fallback."""
        client = AsyncMock()
        client.get.side_effect = httpx.ConnectError("no network")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_http_429_rate_limit_returns_coordinate_string(self):
        """Nominatim 429 Too Many Requests → coordinate fallback."""
        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=_mock_client(_error_response(429))):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_http_500_returns_coordinate_string(self):
        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=_mock_client(_error_response(500))):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_empty_display_name_returns_coordinate_string(self):
        """200 OK but display_name is empty → coordinate fallback."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"display_name": ""}

        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_missing_display_name_key_returns_coordinate_string(self):
        """200 OK but JSON has no display_name key → coordinate fallback."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {}

        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_unexpected_exception_returns_coordinate_string(self):
        """Any unexpected exception (e.g. ValueError) → coordinate fallback."""
        client = AsyncMock()
        client.get.side_effect = ValueError("unexpected")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(reverse_geocode(self._LAT, self._LNG))
        self._assert_fallback(result)

    def test_fallback_format_is_lat_comma_lng(self):
        """Fallback address must be exactly 'lat, lng' as a string."""
        client = AsyncMock()
        client.get.side_effect = httpx.TimeoutException("x")
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__  = AsyncMock(return_value=False)

        lat, lng = 12.9716, 77.5946    # Bengaluru
        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=cm):
            result = run(reverse_geocode(lat, lng))
        assert result["address"] == f"{lat}, {lng}"


# ── reverse_geocode: happy path ───────────────────────────────────────────────

class TestReverseGeocodeSuccess:
    def test_valid_nominatim_response_returned(self):
        resp = _nominatim_ok_response("Nal Stop, Karve Road, Pune, Maharashtra, India")
        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(reverse_geocode(18.5074, 73.8077))
        assert result == {"address": "Nal Stop, Karve Road, Pune, Maharashtra, India"}

    def test_result_always_has_address_key(self):
        resp = _nominatim_ok_response("Some Place")
        ext._geo_last_call = 0.0
        with patch(_ASYNC_CLIENT, return_value=_mock_client(resp)):
            result = run(reverse_geocode(0.0, 0.0))
        assert "address" in result
        assert isinstance(result["address"], str)
