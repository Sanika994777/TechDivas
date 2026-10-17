# CivicFix API Contract (baseline v1)

Baseline written from the planned backend. The frontend audit (Prompt 1) must compare this against what the Lovable pages actually expect and list every mismatch. Prefer adapting the backend response shape to the frontend, or add a mapper in `src/api/`.

## 1. Conventions

- Base URL: `VITE_API_URL` (example: `https://civicfix-api.onrender.com`). All paths below are prefixed with `/api` except `/health`.
- Auth: `Authorization: Bearer <JWT>`. JWT expiry 24h. Roles: `citizen`, `worker`, `admin`.
- Errors: HTTP status plus `{ "detail": "message" }`. Validation errors use 422, auth 401, role 403, rate limit 429, external failure 502.
- Dates: ISO 8601 UTC strings. Distances in meters. IDs are integers. Public identifier is `reference_id`.
- Uploads: `multipart/form-data`, image types `image/jpeg`, `image/png`, `image/webp`, max 5 MB each.

## 2. Enums

| Name | Values |
|---|---|
| status | `Reported`, `Assigned`, `In Progress`, `Resolved`, `Reopened` |
| category | `Pothole`, `Water Leak`, `Garbage`, `Streetlight`, `Other` |
| priority_label | `Critical` (>=75), `High` (>=55), `Medium` (>=35), `Low` |
| role | `citizen`, `worker`, `admin` |
| photo kind | `before`, `after` |
| satisfaction | `null`, `satisfied`, `reopened` |
| reference_id format | `CF-<YYYY>-<6 digits>`, regex `CF-\d{4}-\d{6}` |

Category to team: Pothole -> Roads, Water Leak -> Water, Garbage -> Sanitation, Streetlight -> Electrical.
SLA days: Pothole 7, Water Leak 2, Garbage 3, Streetlight 5, Other 5.

## 3. Shared shapes

```json
// IssueSummary
{
  "id": 12,
  "reference_id": "CF-2026-000012",
  "title": "Deep pothole near school gate",
  "category": "Pothole",
  "status": "Reported",
  "address": "Kothrud, Pune",
  "lat": 18.5074,
  "lng": 73.8077,
  "distance_m": 240,            // only on nearby/similar
  "affected_count": 5,
  "thumbnail": "https://res.cloudinary.com/.../a.jpg",
  "priority": { "score": 72, "label": "High" },
  "created_at": "2026-10-10T08:30:00Z"
}

// Priority breakdown
{
  "score": 72,
  "label": "High",
  "components": { "severity": 80, "community_impact": 60, "time_unresolved": 70 },
  "weights": { "severity": 0.40, "community_impact": 0.35, "time_unresolved": 0.25 }
}

// TimelineItem
{
  "status": "Assigned",
  "note": "Assigned to Roads team",
  "photo_url": null,
  "actor_role": "admin",        // citizen | worker | admin | system
  "created_at": "2026-10-11T09:00:00Z"
}

// IssueDetail (citizen view)
{
  ...IssueSummary,
  "description": "...",
  "photos": [{ "url": "...", "kind": "before" }, { "url": "...", "kind": "after" }],
  "team": { "id": 1, "name": "Roads" } | null,
  "parent_issue_id": null,
  "priority": { Priority breakdown },
  "timeline": [TimelineItem],
  "satisfaction": null,
  "resolved_at": null,
  "has_upvoted": false,
  "is_owner": true
}
```

## 4. Endpoints

### System
| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | public | `{ "status": "ok" }` |

### Auth
| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/api/auth/register` | public | `{ name, email, password (min 8) }` | `{ access_token, token_type, user }` |
| POST | `/api/auth/login` | public | `{ email, password }` | `{ access_token, token_type, role, user }` |
| GET | `/api/auth/me` | any | none | `{ id, name, email, role, team_id }` |

### Issues (citizen)
| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/api/issues/analyze-photo` | citizen | multipart `photo` | `{ suggested_category, severity (1-5), short_description }` (falls back to keyword rules) |
| GET | `/api/geo/reverse?lat&lng` | any | query | `{ address }` (falls back to "lat, lng") |
| GET | `/api/issues/similar?lat&lng&category&text` | citizen | query | `{ items: [IssueSummary + similarity] }` top 5 |
| POST | `/api/issues` | citizen | multipart: `title, description, category, lat, lng, address, photos[1-3]` | `IssueDetail` including `reference_id`, and `duplicate_of` if linked |
| GET | `/api/issues/nearby?lat&lng&radius=500\|1000\|5000&category&status` | any | query | `{ items: [IssueSummary], total }` sorted by distance |
| GET | `/api/issues/mine` | citizen | none | `{ items: [IssueSummary + team + last_update], stats: { total, open, resolved, avg_days } }` |
| GET | `/api/issues/{id}` | any | none | `IssueDetail` |
| POST | `/api/issues/{id}/upvote` | citizen | none | `{ affected_count, has_upvoted }` (toggles) |
| POST | `/api/issues/{id}/feedback` | citizen owner | `{ action: "satisfied" \| "reopen" }` | `IssueDetail` (only when Resolved) |

### Notifications
| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/api/notifications` | any | `{ items: [{ id, issue_id, reference_id, message, is_read, created_at }], unread_count }` |
| POST | `/api/notifications/{id}/read` | any | `{ ok: true }` |

### Public stats (landing page counters)
| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/api/public/stats` | public | `{ total, resolved, avg_resolution_days }` |
| GET | `/api/public/recent-resolved?limit=5` | public | `{ items: [{ reference_id, title, category, area, before_url, after_url, resolved_at }] }` |

### Tracking and bot
| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/api/track/{reference_id}` | public, 20/min/IP | none | `{ reference_id, status, priority_label, category, area, team, last_update: { note, time }, days_open, sla_text, has_after_photo, steps: [{ label, done }] }` (no PII, no exact coordinates) |
| POST | `/api/bot/message` | optional JWT, 20/min/IP | `{ message (max 500), lang?, history?: [{ role, text }] }` | `{ reply, intent, status_card \| null, links: [{ label, path }], suggestions: [string] }` |
| GET | `/api/bot/suggestions` | public | none | `{ items: [string] }` |

### Worker
| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/api/worker/issues?status` | worker | query | `{ items: [IssueSummary + sla_remaining_hours + is_overdue] }` team issues only |
| POST | `/api/worker/issues/{id}/status` | worker | multipart: `status (In Progress \| Resolved), note, photo?` | `IssueDetail`. Resolved requires photo and note, otherwise 422 |

### Admin
| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/api/admin/issues` | admin | query: `sort=priority\|created\|age, status[], category, team_id\|unassigned, priority_label, overdue, has_duplicates, date_from, date_to, q, page, page_size<=50` | `{ items: [AdminIssueRow], total, page, page_size }` where row adds `priority.components, team, auto_suggested_team, age_days, is_overdue` |
| GET | `/api/admin/issues/{id}` | admin | none | `IssueDetail + internal_notes[], linked_reports[], auto_suggested_team` |
| PATCH | `/api/admin/issues/{id}` | admin | `{ title?, description?, category?, severity_override? (1-5) }` | updated detail with recalculated priority |
| POST | `/api/admin/issues/{id}/assign` | admin | `{ team_id }` | updated detail |
| POST | `/api/admin/issues/{id}/status` | admin | multipart: `status, note (5-500), photo?` | updated detail. Resolved requires photo and note. Assigned or In Progress requires a team |
| POST | `/api/admin/issues/bulk-assign` | admin | `{ issue_ids[<=50], team_id }` | `{ assigned: [id], skipped: [{ id, reason }] }` |
| GET | `/api/admin/issues/{id}/notes` | admin | none | `{ items: [{ id, author, text, created_at }] }` |
| POST | `/api/admin/issues/{id}/notes` | admin | `{ text (1-500) }` | the new note |
| GET | `/api/admin/issues/export.csv` | admin | same filters as list | CSV, no reporter PII |
| GET | `/api/admin/map` | admin | none | `{ items: [{ id, reference_id, lat, lng, status, category, priority_label, title, thumbnail }] }` |
| GET | `/api/admin/duplicates` | admin | none | `{ items: [{ id, parent: IssueSummary, duplicate: IssueSummary, distance_m, text_similarity, duplicate_score }] }` |
| POST | `/api/admin/duplicates/{id}/merge` | admin | none | `{ ok: true }` |
| POST | `/api/admin/duplicates/{id}/dismiss` | admin | none | `{ ok: true }` |
| GET | `/api/admin/stats?period=7\|30\|90` | admin | query | see below |
| GET | `/api/admin/teams` | admin | none | `{ items: [{ id, name, categories[], open_count, resolved_this_month, avg_resolution_hours, workers[] }] }` |

Stats response:

```json
{
  "kpis": { "total": 40, "open": 22, "resolved": 18, "avg_resolution_hours": 61.5, "overdue_count": 4 },
  "by_category": [{ "category": "Pothole", "count": 14 }],
  "by_status": [{ "status": "Reported", "count": 8 }],
  "daily_trend": [{ "date": "2026-10-01", "reported": 3, "resolved": 2 }],
  "resolution_by_category": [{ "category": "Pothole", "avg_hours": 70.2 }],
  "resolution_by_team": [{ "team": "Roads", "avg_hours": 66.0 }]
}
```

## 5. Rules the frontend must respect

- Resolved always needs an after photo and a note (worker and admin).
- Internal notes never appear in citizen, track or bot responses.
- Public endpoints never return reporter name, email, phone, exact coordinates or worker names.
- Citizens see only their own complaints under `/mine` and can give feedback only on their own resolved issues.
- Every status change creates a timeline entry with actor role, time, note and optional photo.
- The "server waking up" banner shows if a request takes longer than 8s, with up to 3 retries.

## 6. Open items for the frontend audit (Prompt 1 fills this in)

| Page or component | Field or call the frontend expects | Backend equivalent | Fix |
|---|---|---|---|
| (to be filled by the audit) | | | |
