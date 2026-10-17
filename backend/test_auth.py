"""
Quick integration test for auth endpoints.
Run while the server is up:  python test_auth.py
Checks:
  1. POST /api/auth/register  -> 201, returns access_token + citizen role
  2. POST /api/auth/login     -> 200, returns access_token + role + user
  3. GET  /api/auth/me         -> 200, returns user profile
  4. GET  /api/admin/issues    -> 403 for a citizen (admin-only)
"""

import random
import string
import httpx
import sys

BASE = "http://127.0.0.1:8000"
EMAIL = f"test_{''.join(random.choices(string.ascii_lowercase, k=6))}@example.com"
PASSWORD = "Test1234!"
NAME = "Test User"

passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label} -- {detail}")


print(f"\n=== CivicFix Auth Integration Test ===")
print(f"Using email: {EMAIL}\n")

# ── 1. Register ──────────────────────────────────────────────────────────────
print("1. POST /api/auth/register")
r = httpx.post(f"{BASE}/api/auth/register", json={
    "name": NAME, "email": EMAIL, "password": PASSWORD
})
check("status 201", r.status_code == 201, f"got {r.status_code}: {r.text}")
body = r.json()
check("has access_token", "access_token" in body)
check("role is citizen", body.get("role") == "citizen", f"got {body.get('role')}")
check("user.email matches", body.get("user", {}).get("email") == EMAIL)
TOKEN = body.get("access_token", "")

# ── 2. Login ─────────────────────────────────────────────────────────────────
print("\n2. POST /api/auth/login")
r = httpx.post(f"{BASE}/api/auth/login", json={
    "email": EMAIL, "password": PASSWORD
})
check("status 200", r.status_code == 200, f"got {r.status_code}: {r.text}")
body = r.json()
check("has access_token", "access_token" in body)
check("role is citizen", body.get("role") == "citizen")
check("user.name matches", body.get("user", {}).get("name") == NAME)
TOKEN = body.get("access_token", TOKEN)

# ── 3. /me ───────────────────────────────────────────────────────────────────
print("\n3. GET /api/auth/me")
headers = {"Authorization": f"Bearer {TOKEN}"}
r = httpx.get(f"{BASE}/api/auth/me", headers=headers)
check("status 200", r.status_code == 200, f"got {r.status_code}: {r.text}")
body = r.json()
check("id is int", isinstance(body.get("id"), int))
check("email matches", body.get("email") == EMAIL)
check("role is citizen", body.get("role") == "citizen")

# ── 4. Admin guard (citizen should get 403) ──────────────────────────────────
print("\n4. GET /api/admin/issues (citizen -> 403)")
r = httpx.get(f"{BASE}/api/admin/issues", headers=headers)
check("status 403", r.status_code == 403, f"got {r.status_code}: {r.text}")
check("detail message present", "detail" in r.json(), f"body: {r.text}")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*42}")
print(f"  Passed: {passed}  |  Failed: {failed}")
print(f"{'='*42}\n")
sys.exit(0 if failed == 0 else 1)
