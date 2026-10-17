# CivicFix — API Contract

> Derived from a full read of every frontend file.  
> **No backend code has been written yet.** This document is the single source of truth between frontend expectations and the planned FastAPI backend.

---

## 1. Reference Vocabulary

### 1.1 Status values
Defined in `types/index.ts` and used by `StatusBadge`, `Timeline`, `MiniStepper`, `NearbyPage` filter, `MyComplaintsPage` tabs:

| Value | Meaning |
|---|---|
| `"Reported"` | First state after submission |
| `"Assigned"` | Worker team assigned |
| `"In Progress"` | Work started |
| `"Resolved"` | Issue fixed |
| `"Reopened"` | Citizen rejected resolution |

`MiniStepper` renders only the first four (`Reported → Assigned → In Progress → Resolved`); `Reopened` falls back gracefully (shown as colored dot in Timeline/Badges).

### 1.2 Category values
Defined in `types/index.ts`, `mock-issues.ts` (`CATEGORIES`), `ReportPage`, `NearbyPage`, `TrackPage` (SLA map):

| Value | SLA days (frontend-calculated) |
|---|---|
| `"Pothole"` | 7 |
| `"Water Leak"` | 3 |
| `"Garbage"` | 2 |
| `"Streetlight"` | 5 |
| `"Other"` | 10 |

### 1.3 Priority values
`"Critical"` · `"High"` · `"Medium"` · `"Low"` — rendered by `PriorityBadge`.

### 1.4 Reference ID format
Pattern: `CF-<YYYY>-<6-digit zero-padded number>` — e.g. `CF-2026-000123`.

- Used verbatim in `TrackPage` search input, `ChatWidget` regex match (`CF-\d{4}-\d+`), success screen copy/track, and URL `/issues/:id`.
- **The backend must generate and store IDs in exactly this format.**

---

## 2. Shared Data Shapes

### 2.1 `CivicIssue` (canonical)
Every endpoint that returns an issue **must** return this exact shape. Fields marked `?` are optional; the frontend accesses them conditionally.

```typescript
{
  id:            string;          // "CF-2026-000123"
  title:         string;
  description:   string;
  category:      "Pothole" | "Water Leak" | "Garbage" | "Streetlight" | "Other";
  status:        "Reported" | "Assigned" | "In Progress" | "Resolved" | "Reopened";
  priority:      "Critical" | "High" | "Medium" | "Low";
  address:       string;          // "Karve Road, near Nal Stop, Pune 411004"
  ward:          string;          // "Erandwane · Ward 14"
  lat:           number;          // decimal degrees
  lng:           number;          // decimal degrees
  photos:        string[];        // Cloudinary secure URLs (can be [])
  beforePhoto?:  string | null;   // Cloudinary URL — shown in BeforeAfter on IssueDetailPage
  afterPhoto?:   string | null;   // Cloudinary URL — shown in BeforeAfter on IssueDetailPage
  affectedCount: number;          // upvote/community count
  resolvedCount?: number;         // typed but not rendered
  team:          string;          // "Road Maintenance · Ward 14" | "Awaiting assignment"
  eta:           string;          // "2 days" | "Completed" | "Within 7 days"
  createdAt:     string;          // ISO 8601, e.g. "2026-10-12T09:41:00+05:30"
  updatedAt:     string;          // ISO 8601
  timeline:      TimelineEvent[];
  mine?:         boolean;         // true on /api/issues/me — used by MyComplaintsPage filter
  distance?:     number;          // km from user — used by NearbyPage radius filter, IssueCard
  severity:      number;          // 1–5 — used by IssueDetailPage priority bars
  aiSuggested?:  boolean;         // typed but not rendered
}
```

### 2.2 `TimelineEvent`
Nested inside `CivicIssue.timeline`. Rendered by `Timeline` and `MiniStepper`.

```typescript
{
  status:    "Reported" | "Assigned" | "In Progress" | "Resolved" | "Reopened";
  timestamp: string;   // "Oct 12, 2026 · 9:41 AM"  ← human-readable, NOT ISO 8601
  actor:     string;   // "Citizen" | "System" | "Road Maintenance · Ward 14"
  note:      string;
  photo?:    string;   // Cloudinary URL — shown as 32×80 thumbnail in Timeline
}
```

> **Critical:** `timestamp` is displayed directly as-is. The backend must format it as `"MMM D, YYYY · h:mm AM/PM"` (e.g. `"Oct 12, 2026 · 9:41 AM"`). Sending ISO will render ugly.

### 2.3 `Stats`

```typescript
{
  totalReported:      number;   // e.g. 1842
  totalResolved:      number;   // e.g. 1407
  avgResolutionDays:  number;   // e.g. 4.2 — displayed as "{n} days"
}
```

### 2.4 AI Suggestion (response from `POST /api/ai/suggest`)

```typescript
{
  category:    "Pothole" | "Water Leak" | "Garbage" | "Streetlight" | "Other";
  severity:    number;   // 1–5
  description: string;   // short paragraph shown in the suggestion card
}
```

---

## 3. Endpoints — Complete Specification

### 3.1 Auth

#### `POST /api/auth/register`
**Used by:** `AuthPage` (register mode), `api/client.ts → register()`

Request body (`application/json`):
```json
{ "name": "string", "email": "string", "password": "string" }
```
Response `200`:
```json
{ "token": "string" }
```
Frontend: discards token currently (see Mismatch #1). Backend must return a signed JWT.

---

#### `POST /api/auth/login`
**Used by:** `AuthPage` (login mode)

Request body:
```json
{ "email": "string", "password": "string" }
```
Response `200`:
```json
{ "token": "string" }
```

---

### 3.2 Issues

#### `GET /api/issues`
**Used by:** `LandingPage` (filters `status=Resolved && beforePhoto && afterPhoto`), `NearbyPage` (client-side filter by category/status/radius), `ReportPage` step 3 (client-side filter same category, non-resolved, first 3).

Response `200`: `CivicIssue[]`

Notes:
- Must populate `distance` (km from Pune centre `18.5204, 73.8567`) on every object — see Mismatch #5.
- `mine` flag: set `false` / omit on this endpoint; `true` only on `/api/issues/me`.

---

#### `GET /api/issues/:id`
**Used by:** `IssueDetailPage`

Path param: full reference ID, e.g. `CF-2026-000123`

Response `200`: `CivicIssue`  
Response `404`: any body — frontend shows "not found" state

---

#### `GET /api/issues/me`
**Used by:** `MyComplaintsPage` via `getMyComplaints()`

Auth: `Authorization: Bearer <token>` — see Mismatch #1

Response `200`: `CivicIssue[]` — all with `mine: true`

---

#### `GET /api/issues/nearby`
**Used by:** `api/client.ts → getNearbyIssues()` — **currently dead code** (NearbyPage uses `GET /api/issues`).

Query: `lat`, `lng`, `radius` (km)  
Response `200`: `CivicIssue[]` with `distance` relative to `(lat, lng)`

---

#### `GET /api/issues/track/:ref`
**Used by:** `TrackPage`, `ChatWidget`

Path param: reference ID (case-insensitive, URL-encoded by frontend)

Response `200`: `CivicIssue`  
Response `404`: any body

---

#### `POST /api/issues`
**Used by:** `ReportPage` → `submitIssue()`

Request: **`multipart/form-data`** (frontend uses `FormData`, NOT JSON)

| Field | Type | Constraint |
|---|---|---|
| `title` | string | max 100 chars |
| `description` | string | max 500 chars |
| `category` | string | one of 5 values |
| `lat` | string (form) | coerce to float |
| `lng` | string (form) | coerce to float |
| `address` | string | from Nominatim |
| `photos` | File[] | 0–3, JPEG/PNG/WEBP, max 5 MB each |

Response `200`:
```json
{ "id": "CF-2026-000123" }
```

Backend must:
1. Upload photos to Cloudinary; store secure URLs.
2. Generate `id` as `CF-<YYYY>-<6-digit sequential>`.
3. Auto-assign `priority` from `severity`.
4. Add first `TimelineEvent` (`status: "Reported"`, actor: `"Citizen"`).
5. Set `team = "Awaiting assignment"`, `eta = "Within 7 days"`.
6. Derive `ward` from lat/lng (Overpass or hardcoded lookup) — fallback `""`.

---

#### `POST /api/issues/:id/upvote`
**Used by:** `IssueCard`, `IssueDetailPage`

No auth required (anonymous OK). Response `200`:
```json
{ "affectedCount": 29 }
```
Frontend updates count immediately and disables button (one upvote per session).

---

### 3.3 Stats

#### `GET /api/stats`
**Used by:** `LandingPage`

Response `200`:
```json
{
  "totalReported": 1842,
  "totalResolved": 1407,
  "avgResolutionDays": 4.2
}
```

---

### 3.4 AI

#### `POST /api/ai/suggest`
**Used by:** `ReportPage` step 0 (on photo upload)

> **Note:** frontend currently sends this as `POST` with NO body (see Mismatch #3). Backend must handle an empty body gracefully.

Response `200`:
```json
{
  "category": "Pothole",
  "severity": 4,
  "description": "A significant road damage with visible depression..."
}
```

---

### 3.5 Notifications *(future — not yet wired)*
`MyComplaintsPage` renders `DEMO_NOTIFICATIONS` — a hardcoded static array. No API call exists.

Planned shape when wired:
```json
[{ "id": "string", "text": "string", "time": "string", "read": false }]
```

---

### 3.6 Feedback / Satisfaction *(future — buttons are decorative)*
`IssueDetailPage` shows "Satisfied" / "Reopen" buttons — no `onClick` handler calls any API.

---

### 3.7 Admin
Navbar links to `/admin` but that route does not exist in `App.tsx`. No admin page in the codebase.

---

## 4. Page-by-Page Mock Data Usage

| Page / Component | Mock data | Real API calls |
|---|---|---|
| `LandingPage` | `MOCK_ISSUES`, `MOCK_STATS` | `GET /api/stats`, `GET /api/issues` |
| `ReportPage` | `MOCK_AI_SUGGESTION`; random CF-ID | `POST /api/ai/suggest`, `POST /api/issues`, `GET /api/issues` |
| `NearbyPage` | `MOCK_ISSUES` | `GET /api/issues` |
| `IssueDetailPage` | `MOCK_ISSUES.find()` | `GET /api/issues/:id`, `POST /api/issues/:id/upvote` |
| `MyComplaintsPage` | `MOCK_ISSUES.filter(mine)`, `DEMO_NOTIFICATIONS` (always) | `GET /api/issues/me` |
| `TrackPage` | `MOCK_ISSUES.find()` | `GET /api/issues/track/:ref` |
| `ChatWidget` | Pure JS logic + `trackComplaint()` | `GET /api/issues/track/:ref` |
| `Navbar` | `MOCK_USER = null` (hardcoded) | *(none)* |

---

## 5. Mismatches & Minimal Fixes

### Mismatch #1 — Auth token is never stored or sent
**Problem:** `login()` / `register()` return `{ token }` but it is discarded. `apiFetch` never attaches `Authorization`. So `GET /api/issues/me` always arrives unauthenticated.

**Fix (prefer frontend):** In `client.ts`, after login/register store `token` to `localStorage` and inject `Authorization: Bearer <token>` header in `apiFetch`. ~4 lines. *(Defer to "wire auth" step.)*

**Backend fallback for demo:** Return all issues from `GET /api/issues/me` even without a token (treat as "all issues" for demo mode).

---

### Mismatch #2 — Upvote requires no auth but backend should dedupe
**Problem:** Upvote is called without a token; requiring auth would silently fail.

**Fix (backend adapts):** Accept anonymous upvotes; dedupe by IP or anonymous session cookie. Return `{ affectedCount }` always.

---

### Mismatch #3 — `POST /api/ai/suggest` sends no body
**Problem:** `client.ts` calls `apiFetch("/api/ai/suggest", { method: "POST" })` — no FormData, no JSON. FastAPI with `Body(...)` will 422.

**Fix (backend adapts):** Accept optional/empty body. Call Gemini with a text prompt like _"You are a civic issue classifier. Suggest category (Pothole/Water Leak/Garbage/Streetlight/Other) and severity 1-5 for a reported civic issue in Pune."_ Return deterministic fallback if Gemini fails.

---

### Mismatch #4 — Navbar auth state is hardcoded `null`
**Problem:** After login the UI still shows "Sign In". `UserMenu` is never rendered.

**Fix (frontend, deferred):** Add `useAuth()` context reading `localStorage.token`, decode JWT payload for `name` + `role`. Navbar uses it instead of `MOCK_USER`. *(Defer to "wire auth" step.)*

---

### Mismatch #5 — `distance` must be present on every issue object
**Problem:** `NearbyPage` filter: `(i.distance ?? 99) <= radius` — if `distance` is absent all issues fail `99 <= 0.5`. `ReportPage` similar panel shows `undefined km`.

**Fix (backend):** Always compute `distance` via Haversine from Pune centre `(18.5204, 73.8567)` when no user location is provided. Include in every `CivicIssue` response.

---

### Mismatch #6 — `timeline[].timestamp` must be human-readable, not ISO
**Problem:** `Timeline` renders `event.timestamp` directly with `<Clock /> {event.timestamp}`. ISO strings will display raw.

**Fix (backend):** Format before serialising:
```python
import pytz, datetime
IST = pytz.timezone("Asia/Kolkata")
def fmt_ts(dt: datetime.datetime) -> str:
    # → "Oct 12, 2026 · 9:41 AM"
    return dt.astimezone(IST).strftime("%-b %-d, %Y · %-I:%M %p")
```

---

### Mismatch #7 — Route ordering conflict: `/issues/track/:ref` vs `/issues/:id`
**Problem:** FastAPI matches routes top-to-bottom. If `GET /issues/{id}` is declared first, `/issues/track/CF-2026-000123` will match with `id = "track"`.

**Fix (backend):** Declare specific routes before parametric ones:
```python
@router.get("/issues/me")
@router.get("/issues/nearby")
@router.get("/issues/track/{ref}")
@router.get("/issues/{id}")        # last
```

---

### Mismatch #8 — `POST /api/ai/suggest` sends `Content-Type: application/json` with empty body
**Problem:** `apiFetch` default headers include `"Content-Type": "application/json"` but body is empty string. FastAPI JSON body parser may reject or return 422.

**Fix (backend):** Declare request body as `Optional[dict] = Body(default=None)` and handle `None` gracefully.

---

### Mismatch #9 — Satisfy / Reopen buttons are wired to nothing
**Problem:** Buttons exist in the UI but have no `onClick` handler.

**Fix:** No action for the hackathon demo. Buttons remain decorative. Wire when asked.

---

### Mismatch #10 — Notifications are always static
**Problem:** `MyComplaintsPage` bell shows `DEMO_NOTIFICATIONS` — always the same 3 items, unread count based on hardcoded `read` flags.

**Fix:** No action for demo. Wire `GET /api/notifications` later.

---

### Mismatch #11 — `/admin` route is missing from frontend router
**Problem:** Navbar `<Link to="/admin">` → catch-all redirects to `/`.

**Fix (future):** Add `AdminPage` route to `App.tsx` when backend admin endpoints are built.

---

## 6. Quick-Reference: All Endpoints

| Method | Path | Auth? | Status |
|---|---|---|---|
| `POST` | `/api/auth/register` | No | Needed |
| `POST` | `/api/auth/login` | No | Needed |
| `GET` | `/api/stats` | No | Needed |
| `GET` | `/api/issues` | No | Needed |
| `POST` | `/api/issues` | Optional | Needed |
| `GET` | `/api/issues/me` | JWT | Needed |
| `GET` | `/api/issues/nearby` | No | Dead code — skip for now |
| `GET` | `/api/issues/track/:ref` | No | Needed |
| `GET` | `/api/issues/:id` | No | Needed |
| `POST` | `/api/issues/:id/upvote` | No | Needed |
| `POST` | `/api/ai/suggest` | No | Needed |
| `GET` | `/api/notifications` | JWT | Future |
| `POST` | `/api/issues/:id/satisfy` | JWT | Future |
| `POST` | `/api/issues/:id/reopen` | JWT | Future |

---

## 7. Python Enum / Constant Equivalents

```python
from enum import Enum

class IssueStatus(str, Enum):
    reported    = "Reported"
    assigned    = "Assigned"
    in_progress = "In Progress"
    resolved    = "Resolved"
    reopened    = "Reopened"

class IssueCategory(str, Enum):
    pothole     = "Pothole"
    water_leak  = "Water Leak"
    garbage     = "Garbage"
    streetlight = "Streetlight"
    other       = "Other"

class IssuePriority(str, Enum):
    critical = "Critical"
    high     = "High"
    medium   = "Medium"
    low      = "Low"

def priority_from_severity(s: int) -> IssuePriority:
    return {5: IssuePriority.critical,
            4: IssuePriority.high,
            3: IssuePriority.medium}.get(s, IssuePriority.low)

def make_issue_id(seq: int) -> str:
    import datetime
    year = datetime.date.today().year
    return f"CF-{year}-{seq:06d}"

import pytz, datetime
IST = pytz.timezone("Asia/Kolkata")
def fmt_timestamp(dt: datetime.datetime) -> str:
    """Returns e.g. 'Oct 12, 2026 · 9:41 AM' for direct display in Timeline."""
    return dt.astimezone(IST).strftime("%-b %-d, %Y · %-I:%M %p")
```

---

*File: `/docs/API_CONTRACT.md` — done when reviewed.*
