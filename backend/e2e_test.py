"""Comprehensive E2E test — no special characters in print strings."""
import httpx

BASE = "http://localhost:8000"
EMAIL = "e2e_civicfix@gmail.com"
PWD = "Pass1234!"

results = []

def ok(label):
    results.append(("OK", label))
    print("OK  " + label)

def fail(label, detail=""):
    results.append(("FAIL", label))
    print("FAIL " + label + " " + str(detail))

# ── Register ─────────────────────────────────────────────────────────────────
r = httpx.post(f"{BASE}/api/auth/register",
               json={"name": "E2E Test User", "email": EMAIL, "password": PWD},
               timeout=10)
if r.status_code in (200, 201, 400, 409):
    ok("POST /api/auth/register acceptable status " + str(r.status_code))
else:
    fail("POST /api/auth/register", r.status_code)

# ── Login ─────────────────────────────────────────────────────────────────────
r = httpx.post(f"{BASE}/api/auth/login",
               json={"email": EMAIL, "password": PWD},
               timeout=10)
ok("POST /api/auth/login " + str(r.status_code)) if r.status_code == 200 else fail("POST /api/auth/login", r.text[:100])
login = r.json()
token = login.get("access_token", "")
role = login.get("role", "")
user = login.get("user", {})
ok("login has access_token") if token else fail("login has access_token")
ok("login has role = " + role) if role else fail("login has role")
ok("login has user.name = " + str(user.get("name"))) if user.get("name") else fail("login has user.name")

auth = {"Authorization": "Bearer " + token}

# ── Submit issue ──────────────────────────────────────────────────────────────
form = {
    "title": "E2E Pothole Shivajinagar",
    "description": "Integration test submission from e2e script",
    "category": "Pothole",
    "lat": "18.5204",
    "lng": "73.8567",
    "address": "Shivajinagar, Pune"
}
r = httpx.post(f"{BASE}/api/issues", data=form, headers=auth, timeout=15)
ok("POST /api/issues " + str(r.status_code)) if r.status_code in (200, 201) else fail("POST /api/issues", r.text[:200])
iss = r.json()
ref = iss.get("reference_id", "")
issue_id = iss.get("id", None)
ok("submit returns reference_id " + ref) if ref else fail("submit returns reference_id")
ok("submit returns int id " + str(issue_id)) if isinstance(issue_id, int) else fail("submit returns int id", issue_id)

# ── Get by reference_id ───────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/issues/{ref}", timeout=10)
ok("GET /api/issues/{ref} " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/issues/{ref}", r.status_code)
d = r.json()
ok("detail.reference_id matches") if d.get("reference_id") == ref else fail("detail.reference_id matches", d.get("reference_id"))
ok("detail.timeline is list") if isinstance(d.get("timeline"), list) else fail("detail.timeline is list")
ok("detail.photos is list") if isinstance(d.get("photos"), list) else fail("detail.photos is list")

# ── Get by integer id ─────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/issues/{issue_id}", timeout=10)
ok("GET /api/issues/{int_id} " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/issues/{int_id}", r.status_code)

# ── Upvote ────────────────────────────────────────────────────────────────────
r = httpx.post(f"{BASE}/api/issues/{issue_id}/upvote", headers=auth, timeout=10)
ok("POST /api/issues/{id}/upvote " + str(r.status_code)) if r.status_code == 200 else fail("POST upvote", r.text[:100])
uv = r.json()
ok("upvote.affected_count = " + str(uv.get("affected_count"))) if "affected_count" in uv else fail("upvote.affected_count missing")

# ── Track ─────────────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/track/{ref}", timeout=10)
ok("GET /api/track/{ref} " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/track/{ref}", r.text[:100])
tr = r.json()
ok("track.status = " + str(tr.get("status"))) if tr.get("status") else fail("track.status missing")
ok("track has no lat/lng") if "lat" not in tr and "lng" not in tr else fail("track leaks coordinates")
ok("track has no reporter email") if "email" not in str(tr) else fail("track leaks email")

# ── Nearby ────────────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/issues/nearby?lat=18.5204&lng=73.8567&radius=5000", timeout=10)
ok("GET /api/issues/nearby " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/issues/nearby", r.status_code)
items = r.json().get("items", [])
ok("nearby returns " + str(len(items)) + " items") if isinstance(items, list) else fail("nearby items not a list")

# ── Mine ──────────────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/issues/mine", headers=auth, timeout=10)
ok("GET /api/issues/mine " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/issues/mine", r.status_code)
mine = r.json().get("items", [])
ok("mine returns list with " + str(len(mine)) + " items")

# ── Geo reverse ───────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/geo/reverse?lat=18.5204&lng=73.8567", timeout=10)
ok("GET /api/geo/reverse " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/geo/reverse", r.status_code)
geo = r.json()
has_addr = bool(geo.get("display_name") or geo.get("address"))
ok("geo has address: " + str(geo)) if has_addr else ok("geo fallback: " + str(geo))

# ── Bot ───────────────────────────────────────────────────────────────────────
r = httpx.post(f"{BASE}/api/bot/message",
               json={"message": "Help me track my complaint"},
               timeout=15)
ok("POST /api/bot/message " + str(r.status_code)) if r.status_code == 200 else fail("POST /api/bot/message", r.text[:100])
bot = r.json()
ok("bot.reply present: " + bot.get("reply", "")[:60]) if bot.get("reply") else fail("bot.reply missing")

# ── Notifications ─────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/notifications", headers=auth, timeout=10)
ok("GET /api/notifications " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/notifications", r.status_code)
ok("notifications is list with " + str(len(r.json())) + " items") if isinstance(r.json(), list) else fail("notifications not a list")

# ── Recent resolved ───────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/public/recent-resolved?limit=6", timeout=10)
ok("GET /api/public/recent-resolved " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/public/recent-resolved", r.text[:100])

# ── Stats ─────────────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/api/public/stats", timeout=10)
ok("GET /api/public/stats " + str(r.status_code)) if r.status_code == 200 else fail("GET /api/public/stats", r.status_code)

# ── Analyze photo (no image → fallback) ──────────────────────────────────────
import io
files = {"photo": ("test.jpg", io.BytesIO(b""), "image/jpeg")}
r = httpx.post(f"{BASE}/api/issues/analyze-photo", files=files, headers=auth, timeout=15)
ok("POST /api/issues/analyze-photo " + str(r.status_code)) if r.status_code == 200 else fail("POST analyze-photo", r.text[:100])
if r.status_code == 200:
    ai = r.json()
    ok("ai.suggested_category = " + str(ai.get("suggested_category"))) if ai.get("suggested_category") else fail("ai.suggested_category missing")

print()
passed = sum(1 for s, _ in results if s == "OK")
failed = sum(1 for s, _ in results if s == "FAIL")
print("PASSED: " + str(passed) + "/" + str(passed + failed))
if failed:
    print("FAILED CHECKS:")
    for s, l in results:
        if s == "FAIL":
            print("  - " + l)
else:
    print("ALL CHECKS PASSED")
