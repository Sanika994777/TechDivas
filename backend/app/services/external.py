"""
services/external.py
────────────────────────────────────────────────────────────────────────────
External HTTP calls for CivicFix.  Two public coroutines:

  analyze_photo(image_bytes, *, content_type, title, description)
      Calls Gemini 1.5-Flash via REST (GEMINI_API_KEY).
      Returns {"suggested_category", "severity" (1-5), "short_description"}.
      Falls back to keyword-rule matching on title/description, or the bare
      sentinel {"suggested_category": "Other", "severity": 3, …} when no
      keyword matches either.

  reverse_geocode(lat, lng)
      Calls Nominatim (OpenStreetMap) with a proper User-Agent header.
      Rate-limited to 1 req/s (OSM policy) via an asyncio.Lock + sleep.
      Returns {"address": "<human readable>"}.
      Falls back to {"address": "lat, lng"}.

Design rules (for every external call in this module):
  • httpx.AsyncClient with timeout=5 s (connect + read combined).
  • All exceptions caught inside the function — nothing propagates to caller.
  • No import-time side effects that could fail (key is read lazily).
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
from typing import Any

import httpx

from app.core.config import settings  # module-level — patchable in tests

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_TIMEOUT = httpx.Timeout(5.0)          # 5 s connect + read
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_NOMINATIM_UA  = "CivicFix-Hackathon/1.0"

# Valid categories used throughout the app (mirrors CategoryEnum values)
VALID_CATEGORIES = {"Pothole", "Water Leak", "Garbage", "Streetlight", "Other"}

# Keyword → category mapping for the offline fallback
_KEYWORD_RULES: list[tuple[list[str], str, int]] = [
    # (keywords, suggested_category, default_severity)
    (["pothole", "crater", "road damage", "road repair", "broken road", "bump"],
     "Pothole", 3),
    (["water leak", "burst pipe", "flooding", "waterlogging", "drain overflow",
      "sewage", "sewer", "overflow", "leaking pipe", "water main", "leak"],
     "Water Leak", 4),
    (["garbage", "waste", "trash", "litter", "dumping", "rubbish", "refuse",
      "sanitation", "dirty", "filth"],
     "Garbage", 2),
    (["streetlight", "street light", "lamp post", "light out", "dark road",
      "no light", "electricity", "electric pole", "broken light"],
     "Streetlight", 2),
]

# ── Nominatim rate-limiter (1 req / s) ───────────────────────────────────────

_geo_lock = asyncio.Lock()
_geo_last_call: float = 0.0          # monotonic timestamp of last call


# ── Helpers ──────────────────────────────────────────────────────────────────

def _keyword_fallback(title: str, description: str) -> dict[str, Any]:
    """
    Scan title + description for known keywords and return the best matching
    category/severity.  Returns the bare sentinel if no keywords match.
    """
    haystack = (title + " " + description).lower()
    for keywords, category, severity in _KEYWORD_RULES:
        if any(kw in haystack for kw in keywords):
            return {
                "suggested_category": category,
                "severity": severity,
                "short_description": "Detected from issue text. Please verify.",
            }
    return {
        "suggested_category": "Other",
        "severity": 3,
        "short_description": "Could not classify automatically. Please fill in details.",
    }


def _parse_gemini_response(text: str) -> dict[str, Any] | None:
    """
    Extract the first JSON object from Gemini's response text.
    Returns None if parsing fails or result is unusable.
    """
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    category = str(data.get("suggested_category", "")).strip()
    if category not in VALID_CATEGORIES:
        category = "Other"

    try:
        severity = max(1, min(5, int(data.get("severity", 3))))
    except (TypeError, ValueError):
        severity = 3

    short_desc = str(data.get("short_description", "")).strip()[:100] or "Civic issue detected."

    return {
        "suggested_category": category,
        "severity": severity,
        "short_description": short_desc,
    }


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_photo(
    image_bytes: bytes,
    *,
    content_type: str = "image/jpeg",
    title: str = "",
    description: str = "",
) -> dict[str, Any]:
    """
    Analyse a photo via Gemini 1.5-Flash and return a classification dict:
        {
            "suggested_category": str,   # one of VALID_CATEGORIES
            "severity":           int,   # 1-5
            "short_description":  str,   # ≤100 chars
        }

    Falls back gracefully (keyword rules → sentinel) on:
      - Missing / empty GEMINI_API_KEY
      - Network error or timeout (5 s)
      - Non-2xx HTTP response
      - Unparseable JSON in model output
      - Any other exception
    Never raises.
    """
    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY not set — using keyword fallback.")
        return _keyword_fallback(title, description)

    b64_image = base64.b64encode(image_bytes).decode()
    prompt = (
        "You are a civic-issue classifier. Analyse the photo and reply with "
        "ONLY a single JSON object — no markdown, no prose — using exactly "
        "these keys:\n"
        "  suggested_category  (one of: Pothole, Water Leak, Garbage, Streetlight, Other)\n"
        "  severity            (integer 1-5, where 5 is most severe)\n"
        "  short_description   (max 100 chars, plain English)\n"
        "Example: {\"suggested_category\": \"Pothole\", \"severity\": 3, "
        "\"short_description\": \"Large pothole on road surface.\"}"
    )
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": content_type, "data": b64_image}},
            ]
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _GEMINI_URL,
                params={"key": api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()
            # Navigate: candidates[0].content.parts[0].text
            raw_text: str = (
                body["candidates"][0]["content"]["parts"][0]["text"]
            )
            parsed = _parse_gemini_response(raw_text)
            if parsed:
                return parsed
            logger.warning("Gemini returned unparseable text — using keyword fallback.")
    except httpx.TimeoutException:
        logger.warning("Gemini request timed out (>5 s) — using keyword fallback.")
    except httpx.HTTPStatusError as exc:
        logger.warning("Gemini HTTP %s — using keyword fallback.", exc.response.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini call failed (%s: %s) — using keyword fallback.",
                       type(exc).__name__, exc)

    return _keyword_fallback(title, description)


async def reverse_geocode(lat: float, lng: float) -> dict[str, str]:
    """
    Reverse-geocode (lat, lng) via Nominatim and return {"address": <str>}.

    - At most 1 request per second (OSM usage policy), enforced with an
      asyncio.Lock + sleep.
    - 5 s httpx timeout.
    - Falls back to {"address": "lat, lng"} on any failure.
    Never raises.
    """
    global _geo_last_call

    fallback = {"address": f"{lat}, {lng}"}

    async with _geo_lock:
        # Enforce ≥1 s gap between requests
        now = time.monotonic()
        gap = now - _geo_last_call
        if gap < 1.0:
            await asyncio.sleep(1.0 - gap)
        _geo_last_call = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    _NOMINATIM_URL,
                    params={
                        "lat": lat,
                        "lon": lng,
                        "format": "json",
                        "addressdetails": "0",
                        "zoom": "16",
                    },
                    headers={"User-Agent": _NOMINATIM_UA},
                )
                resp.raise_for_status()
                body = resp.json()
                address = body.get("display_name", "").strip()
                if not address:
                    return fallback
                return {"address": address}

        except httpx.TimeoutException:
            logger.warning("Nominatim request timed out (>5 s) — using coordinate fallback.")
        except httpx.HTTPStatusError as exc:
            logger.warning("Nominatim HTTP %s — using coordinate fallback.",
                           exc.response.status_code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nominatim call failed (%s: %s) — using coordinate fallback.",
                           type(exc).__name__, exc)

    return fallback
