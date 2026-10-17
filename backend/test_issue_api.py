"""
Smoke test: POST /api/issues with a real JPEG photo.
Run from backend/ directory.
"""
import io
import requests

BASE = "http://127.0.0.1:8000"

# 1. Login
print("1. Logging in...")
r = requests.post(f"{BASE}/api/auth/login", json={
    "email": "citizen@demo.com",
    "password": "Demo@1234"
}, timeout=15)
r.raise_for_status()
token = r.json()["access_token"]
print(f"   Token OK (role={r.json()['role']})")

headers = {"Authorization": f"Bearer {token}"}

# 2. Fetch a small test JPEG from picsum
print("2. Fetching test image...")
img_resp = requests.get("https://picsum.photos/300/200.jpg", timeout=10)
img_resp.raise_for_status()
img_bytes = img_resp.content
print(f"   Image fetched: {len(img_bytes)} bytes, content-type={img_resp.headers.get('Content-Type')}")

# 3. POST /api/issues with the photo
print("3. Creating issue...")
r2 = requests.post(
    f"{BASE}/api/issues",
    headers=headers,
    data={
        "title": "Test pothole on MG Road",
        "description": "Large pothole causing traffic issues near MG Road signal.",
        "category": "Pothole",
        "lat": "18.5204",
        "lng": "73.8567",
        "address": "MG Road, Pune 411001",
    },
    files={
        "photos": ("test_issue.jpg", io.BytesIO(img_bytes), "image/jpeg"),
    },
    timeout=40,
)

if r2.status_code == 201:
    data = r2.json()
    print(f"\n   SUCCESS (201 Created)")
    print(f"   reference_id : {data['reference_id']}")
    print(f"   status       : {data['status']}")
    print(f"   priority     : {data['priority']['label']} ({data['priority']['score']})")
    print(f"   photos       : {len(data['photos'])} photo(s)")
    for p in data["photos"]:
        print(f"      [{p['kind']}] {p['url']}")
    print(f"   timeline     : {len(data['timeline'])} event(s)")
    print(f"   team         : {data.get('team')}")
else:
    print(f"\n   ERROR {r2.status_code}: {r2.text}")

# 4. GET /api/issues/{id} for the new issue
if r2.status_code == 201:
    issue_id = data["id"]
    print(f"\n4. GET /api/issues/{issue_id}...")
    r3 = requests.get(f"{BASE}/api/issues/{issue_id}", timeout=10)
    r3.raise_for_status()
    d3 = r3.json()
    print(f"   reference_id : {d3['reference_id']}")
    print(f"   photos       : {d3['photos']}")
    print(f"   timeline     : {[t['status'] for t in d3['timeline']]}")
    print(f"   priority components: {d3['priority']['components']}")

# 5. Validation error tests
print("\n5. Validation tests...")

# Wrong content type
print("   - Wrong content type (text/plain) ...")
bad_type = requests.post(
    f"{BASE}/api/issues",
    headers=headers,
    data={"title":"X","description":"Y","category":"Pothole","lat":"18.5","lng":"73.8","address":"A"},
    files={"photos": ("bad.txt", io.BytesIO(b"hello"), "text/plain")},
    timeout=10,
)
print(f"     Status: {bad_type.status_code} — {bad_type.json().get('detail','')[:80]}")

# Too large file (6 MB of zeros)
print("   - Oversized file (6 MB) ...")
big_file = requests.post(
    f"{BASE}/api/issues",
    headers=headers,
    data={"title":"X","description":"Y","category":"Pothole","lat":"18.5","lng":"73.8","address":"A"},
    files={"photos": ("big.jpg", io.BytesIO(b"\x00" * 6 * 1024 * 1024), "image/jpeg")},
    timeout=15,
)
print(f"     Status: {big_file.status_code} — {big_file.json().get('detail','')[:80]}")

# Bad category
print("   - Invalid category ...")
bad_cat = requests.post(
    f"{BASE}/api/issues",
    headers=headers,
    data={"title":"X","description":"Y","category":"Unicorn","lat":"18.5","lng":"73.8","address":"A"},
    timeout=10,
)
print(f"     Status: {bad_cat.status_code} — {bad_cat.json().get('detail','')[:80]}")

print("\nDone.")
