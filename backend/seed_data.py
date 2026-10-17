"""
Seed script — creates teams, workers, and dummy issues so the Admin and
Worker dashboards have real data to display.

Run once:
  python seed_data.py

Safe to run multiple times — skips existing records.
"""
import sys, random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

from app.core.database import get_db
from app.core.security import hash_password
from app.models import (
    Team, User, Issue, StatusHistory, IssuePhoto,
    RoleEnum, StatusEnum, CategoryEnum, PhotoKindEnum,
)

db = next(get_db())

def utcnow():
    return datetime.now(timezone.utc)

# ── 1. Teams ──────────────────────────────────────────────────────────────────
TEAMS = [
    {"name": "Roads",                  "categories": "Pothole,Other"},
    {"name": "Water",                  "categories": "Water Leak"},
    {"name": "Sanitation & Electrical","categories": "Garbage,Streetlight"},
]

team_objs = {}
for t in TEAMS:
    existing = db.query(Team).filter(Team.name == t["name"]).first()
    if not existing:
        obj = Team(name=t["name"], categories=t["categories"])
        db.add(obj)
        db.flush()
        print(f"  [Team] Created: {t['name']}")
    else:
        obj = existing
        print(f"  [Team] Already exists: {t['name']}")
    team_objs[t["name"]] = obj

db.commit()

# ── 2. Admin ──────────────────────────────────────────────────────────────────
ADMIN_EMAIL = "admin@civicfix.com"
admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
if not admin:
    admin = User(
        name="Admin User",
        email=ADMIN_EMAIL,
        password_hash=hash_password("Admin1234"),
        role=RoleEnum.admin,
    )
    db.add(admin)
    db.flush()
    print(f"  [Admin] Created: {ADMIN_EMAIL} / Admin1234")
else:
    admin.role = RoleEnum.admin
    print(f"  [Admin] Already exists: {ADMIN_EMAIL}")
db.commit()

# ── 3. Workers (one per team) ─────────────────────────────────────────────────
WORKERS = [
    {"name": "Rajesh Kumar",   "email": "worker.roads@civicfix.com",    "team": "Roads"},
    {"name": "Priya Sharma",   "email": "worker.water@civicfix.com",    "team": "Water"},
    {"name": "Amit Patil",     "email": "worker.sanit@civicfix.com",    "team": "Sanitation & Electrical"},
]

worker_objs = []
for w in WORKERS:
    existing = db.query(User).filter(User.email == w["email"]).first()
    team = team_objs[w["team"]]
    if not existing:
        obj = User(
            name=w["name"],
            email=w["email"],
            password_hash=hash_password("Worker1234"),
            role=RoleEnum.worker,
            team_id=team.id,
        )
        db.add(obj)
        db.flush()
        print(f"  [Worker] Created: {w['email']} / Worker1234  team={w['team']}")
    else:
        existing.role = RoleEnum.worker
        existing.team_id = team.id
        obj = existing
        print(f"  [Worker] Updated: {w['email']}  team={w['team']}")
    worker_objs.append(obj)
db.commit()

# ── 4. Citizen reporter ───────────────────────────────────────────────────────
CITIZEN_EMAIL = "citizen@civicfix.com"
citizen = db.query(User).filter(User.email == CITIZEN_EMAIL).first()
if not citizen:
    citizen = User(
        name="Demo Citizen",
        email=CITIZEN_EMAIL,
        password_hash=hash_password("Citizen1234"),
        role=RoleEnum.citizen,
    )
    db.add(citizen)
    db.flush()
    print(f"  [Citizen] Created: {CITIZEN_EMAIL} / Citizen1234")
else:
    print(f"  [Citizen] Already exists: {CITIZEN_EMAIL}")
db.commit()

# ── 5. Dummy issues ───────────────────────────────────────────────────────────
ISSUES = [
    {
        "title": "Large pothole near Shivajinagar Station",
        "description": "Deep pothole causing tyre damage on FC Road.",
        "category": CategoryEnum.Pothole,
        "address": "FC Road, Shivajinagar, Pune",
        "lat": 18.5308, "lng": 73.8474,
        "severity": 4,
        "status": StatusEnum.Assigned,
        "team": "Roads",
        "days_ago": 5,
    },
    {
        "title": "Burst water pipe on MG Road",
        "description": "Water gushing since morning, road flooded.",
        "category": CategoryEnum.WaterLeak,
        "address": "MG Road, Camp, Pune",
        "lat": 18.5167, "lng": 73.8769,
        "severity": 5,
        "status": StatusEnum.InProgress,
        "team": "Water",
        "days_ago": 2,
    },
    {
        "title": "Garbage not collected for 3 days",
        "description": "Overflowing bins near Baner market.",
        "category": CategoryEnum.Garbage,
        "address": "Baner Road, Pune",
        "lat": 18.5590, "lng": 73.7868,
        "severity": 3,
        "status": StatusEnum.Reported,
        "team": "Sanitation & Electrical",
        "days_ago": 3,
    },
    {
        "title": "Streetlight out on Karve Road",
        "description": "Three consecutive lights not working since last week.",
        "category": CategoryEnum.Streetlight,
        "address": "Karve Road, Kothrud, Pune",
        "lat": 18.5004, "lng": 73.8165,
        "severity": 3,
        "status": StatusEnum.Assigned,
        "team": "Sanitation & Electrical",
        "days_ago": 7,
    },
    {
        "title": "Pothole on Pune-Nashik Highway",
        "description": "Multiple potholes causing accidents near toll.",
        "category": CategoryEnum.Pothole,
        "address": "Pune-Nashik Highway, Nashik Phata",
        "lat": 18.6240, "lng": 73.7896,
        "severity": 5,
        "status": StatusEnum.Resolved,
        "team": "Roads",
        "days_ago": 15,
    },
    {
        "title": "Drain overflow at Koregaon Park",
        "description": "Blocked storm drain causing flooding in the lane.",
        "category": CategoryEnum.Other,
        "address": "Lane 5, Koregaon Park, Pune",
        "lat": 18.5362, "lng": 73.8940,
        "severity": 4,
        "status": StatusEnum.InProgress,
        "team": "Sanitation & Electrical",
        "days_ago": 4,
    },
    {
        "title": "Water supply disrupted in Hadapsar",
        "description": "No water supply for 2 days in the sector.",
        "category": CategoryEnum.WaterLeak,
        "address": "Hadapsar, Pune",
        "lat": 18.5018, "lng": 73.9260,
        "severity": 4,
        "status": StatusEnum.Reported,
        "team": "Water",
        "days_ago": 1,
    },
    {
        "title": "Broken pavement near Deccan Gymkhana",
        "description": "Tiles broken and upturned, dangerous for pedestrians.",
        "category": CategoryEnum.Other,
        "address": "Deccan Gymkhana, Pune",
        "lat": 18.5162, "lng": 73.8403,
        "severity": 2,
        "status": StatusEnum.Reported,
        "team": "Roads",
        "days_ago": 6,
    },
]

# Reference ID counter
existing_count = db.query(Issue).count()

def make_ref(n):
    year = 2026
    return f"CF-{year}-{n:06d}"

created_issues = 0
for idx, data in enumerate(ISSUES):
    # Skip if similar title already exists
    existing = db.query(Issue).filter(Issue.title == data["title"]).first()
    if existing:
        print(f"  [Issue] Already exists: {data['title'][:50]}")
        continue

    existing_count += 1
    ref = make_ref(existing_count)
    team = team_objs[data["team"]]
    created_at = utcnow() - timedelta(days=data["days_ago"])

    issue = Issue(
        reference_id   = ref,
        title          = data["title"],
        description    = data["description"],
        category       = data["category"],
        address        = data["address"],
        lat            = data["lat"],
        lng            = data["lng"],
        status         = data["status"],
        severity       = data["severity"],
        affected_count = random.randint(3, 40),
        priority_score = data["severity"] * 15.0,
        reporter_id    = citizen.id,
        team_id        = team.id,
        created_at     = created_at,
    )
    if data["status"] == StatusEnum.Resolved:
        issue.resolved_at = utcnow() - timedelta(days=1)

    db.add(issue)
    db.flush()

    # Timeline entries
    db.add(StatusHistory(
        issue_id   = issue.id,
        status     = StatusEnum.Reported,
        note       = "Issue reported via CivicFix.",
        actor_role = "citizen",
        changed_by = citizen.id,
        created_at = created_at,
    ))

    if data["status"] in (StatusEnum.Assigned, StatusEnum.InProgress, StatusEnum.Resolved):
        db.add(StatusHistory(
            issue_id   = issue.id,
            status     = StatusEnum.Assigned,
            note       = f"Assigned to {team.name} team.",
            actor_role = "admin",
            changed_by = admin.id,
            created_at = created_at + timedelta(hours=3),
        ))

    if data["status"] in (StatusEnum.InProgress, StatusEnum.Resolved):
        db.add(StatusHistory(
            issue_id   = issue.id,
            status     = StatusEnum.InProgress,
            note       = "Team has started work on the issue.",
            actor_role = "worker",
            changed_by = worker_objs[0].id,
            created_at = created_at + timedelta(hours=8),
        ))

    if data["status"] == StatusEnum.Resolved:
        db.add(StatusHistory(
            issue_id   = issue.id,
            status     = StatusEnum.Resolved,
            note       = "Issue has been resolved. Site inspected and confirmed clear.",
            actor_role = "worker",
            changed_by = worker_objs[0].id,
            created_at = utcnow() - timedelta(days=1),
        ))

    print(f"  [Issue] Created: [{ref}] {data['title'][:50]}  status={data['status'].value}")
    created_issues += 1

db.commit()

print()
print("=" * 60)
print("SEED COMPLETE")
print("=" * 60)
print()
print("Login credentials:")
print(f"  ADMIN   : admin@civicfix.com      / Admin1234")
print(f"  WORKERS : worker.roads@civicfix.com   / Worker1234")
print(f"          : worker.water@civicfix.com   / Worker1234")
print(f"          : worker.sanit@civicfix.com   / Worker1234")
print(f"  CITIZEN : citizen@civicfix.com    / Citizen1234")
print()
print(f"  Teams created : {len(team_objs)}")
print(f"  Issues created: {created_issues}")
print()
print("Open http://localhost:5173/login")
