#!/usr/bin/env python3
"""
CivicFix — idempotent seed script.
Safe to re-run: every insert is guarded by a "skip if exists" check.

Usage (from the backend/ directory):
    python seed.py

Requires ../.env.txt (or env vars) with DATABASE_URL and JWT_SECRET set.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make sure `app` package is importable when run as `python seed.py`
sys.path.insert(0, str(Path(__file__).parent))

# Load settings (reads ../.env.txt relative to CWD = backend/)
from app.core.config import settings  # noqa: E402  triggers .env.txt load
from app.core.database import engine, SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    CategoryEnum,
    Issue,
    IssuePhoto,
    Notification,
    PhotoKindEnum,
    RoleEnum,
    StatusEnum,
    StatusHistory,
    Team,
    User,
    Upvote,
)
import bcrypt as _bcrypt

def _hash_password(plain: str) -> str:
    """Hash a password using bcrypt directly (bypasses passlib/bcrypt v5 compat issue)."""
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()

# ── Helpers ──────────────────────────────────────────────────────────────────

UTC = timezone.utc


def utc(days_ago: int, hour: int = 9, minute: int = 30) -> datetime:
    """Return a UTC datetime N days ago at the given local IST hour (IST = UTC+5:30)."""
    ist_offset = timedelta(hours=5, minutes=30)
    ist_now = datetime.now(UTC) + ist_offset           # approximate IST "now"
    ist_target = ist_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    ist_target -= timedelta(days=days_ago)
    return (ist_target - ist_offset).replace(tzinfo=UTC)


def fmt_ts(dt: datetime) -> str:
    """Human-readable timestamp for timeline notes (matches frontend expectation)."""
    ist = dt + timedelta(hours=5, minutes=30)
    return ist.strftime("%-d %b %Y · %-I:%M %p")      # e.g. "12 Oct 2026 · 9:41 AM"


# ── Priority engine (real service) ──────────────────────────────────────────

from app.services.priority import calculate_priority


def compute_priority_score_for_seed(issue: "Issue") -> float:
    """Delegate to the real priority engine and return the numeric score."""
    return calculate_priority(issue).score


# ── Placeholder photo URLs (no Cloudinary uploads in seed) ───────────────────

P = {
    "pothole":      "https://images.unsplash.com/photo-1584463699057-a0e29c6ea4fb?w=600",
    "pothole2":     "https://images.unsplash.com/photo-1617471346061-5d329ab9c574?w=600",
    "water":        "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?w=600",
    "garbage":      "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=600",
    "streetlight":  "https://images.unsplash.com/photo-1542621334-a254cf47733d?w=600",
    "drain":        "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=600",
    "construction": "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?w=600",
    "road_fixed":   "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600",
    "area_clean":   "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600",
    "pipe_fixed":   "https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=600",
}

# ── Static data ───────────────────────────────────────────────────────────────

DEMO_PASSWORD = "Demo@1234"

TEAMS_DATA = [
    {"name": "Roads",                  "categories": "Pothole,Other"},
    {"name": "Water",                  "categories": "Water Leak"},
    {"name": "Sanitation & Electrical","categories": "Garbage,Streetlight"},
]

USERS_DATA = [
    {"name": "Demo Citizen", "email": "citizen@demo.com", "role": RoleEnum.citizen, "team": None},
    {"name": "Demo Worker",  "email": "worker@demo.com",  "role": RoleEnum.worker,  "team": "Roads"},
    {"name": "Demo Admin",   "email": "admin@demo.com",   "role": RoleEnum.admin,   "team": None},
]

# Each issue dict keys:
#   ref, title, desc, cat, status, sev, addr, lat, lng, votes,
#   photos (list of "before" URLs), before_url, after_url,
#   team (team name | None), days (days_ago_created), ai, parent (ref | None)
ISSUES_DATA = [

    # ── Potholes ──────────────────────────────────────────────────────────────
    dict(ref="CF-2026-000001",
         title="Deep pothole near Nal Stop bus stand",
         desc="A large pothole on Karve Road near Nal Stop. About 45 cm wide and 18 cm deep. "
              "Several two-wheelers have skidded. Urgent repair needed.",
         cat=CategoryEnum.Pothole, status=StatusEnum.InProgress, sev=4,
         addr="Karve Road, near Nal Stop, Kothrud, Pune 411038",
         lat=18.5074, lng=73.8077, votes=28,
         photos=[P["pothole"], P["pothole2"]], before_url=P["pothole"], after_url=None,
         team="Roads", days=15, ai=True, parent=None),

    dict(ref="CF-2026-000002",
         title="Pothole blocking traffic on FC Road",
         desc="A pothole spanning half the lane on FC Road near Shivajinagar flyover. "
              "Vehicles swerving dangerously to avoid it.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Assigned, sev=3,
         addr="FC Road, near Shivajinagar Flyover, Pune 411016",
         lat=18.5308, lng=73.8490, votes=15,
         photos=[P["pothole"]], before_url=None, after_url=None,
         team="Roads", days=8, ai=False, parent=None),

    dict(ref="CF-2026-000003",
         title="Multiple potholes on Sinhagad Road, Katraj",
         desc="At least 6 large potholes in a 200 m stretch of Sinhagad Road. "
              "Heavy vehicles have worsened them. Pedestrians crossing are at risk.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Reported, sev=4,
         addr="Sinhagad Road, Katraj, Pune 411046",
         lat=18.4524, lng=73.8572, votes=22,
         photos=[P["pothole2"]], before_url=None, after_url=None,
         team=None, days=3, ai=True, parent=None),

    dict(ref="CF-2026-000004",
         title="Road cave-in in front of PMC office, Shivajinagar",
         desc="Large depression in the road directly in front of the PMC main office. "
              "Likely a subsurface pipe failure. Significant traffic disruption.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Resolved, sev=5,
         addr="Shivajinagar, near PMC Office, Pune 411005",
         lat=18.5308, lng=73.8469, votes=45,
         photos=[P["pothole"], P["pothole2"]],
         before_url=P["pothole"], after_url=P["road_fixed"],
         team="Roads", days=38, ai=False, parent=None),

    dict(ref="CF-2026-000005",
         title="Road surface damage near Hadapsar bus terminal",
         desc="Large sunken area near Hadapsar bus terminal. PMPML buses are avoiding "
              "the stretch, causing service disruption.",
         cat=CategoryEnum.Pothole, status=StatusEnum.InProgress, sev=4,
         addr="Hadapsar Main Road, near Bus Terminal, Pune 411028",
         lat=18.5018, lng=73.9274, votes=31,
         photos=[P["pothole"]], before_url=P["pothole"], after_url=None,
         team="Roads", days=12, ai=True, parent=None),

    dict(ref="CF-2026-000006",
         title="Sunken road patch near Baner petrol pump",
         desc="Road has subsided near the petrol pump on Baner Road. "
              "The patch is about 30 cm below level. Water collects here in rains.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Assigned, sev=3,
         addr="Baner Road, near Petrol Pump, Pune 411045",
         lat=18.5590, lng=73.7868, votes=18,
         photos=[P["pothole2"]], before_url=None, after_url=None,
         team="Roads", days=6, ai=False, parent=None),

    dict(ref="CF-2026-000007",
         title="Pothole blocking left lane — Viman Nagar service road",
         desc="Large pothole blocking the left lane of the service road in Viman Nagar "
              "near Seasons Mall. Causing daily traffic slowdowns.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Resolved, sev=4,
         addr="Viman Nagar Road, near Seasons Mall, Pune 411014",
         lat=18.5679, lng=73.9143, votes=28,
         photos=[P["pothole"]],
         before_url=P["pothole"], after_url=P["road_fixed"],
         team="Roads", days=30, ai=False, parent=None),

    dict(ref="CF-2026-000008",
         title="Damaged road near Kothrud school gate",
         desc="Road near the entrance of the school on Karve Nagar has cracked "
              "and become uneven. Children and parents are tripping.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Reported, sev=3,
         addr="Near Municipal School, Karve Nagar, Kothrud, Pune 411038",
         lat=18.5060, lng=73.8095, votes=12,
         photos=[P["pothole2"]], before_url=None, after_url=None,
         team=None, days=2, ai=False, parent=None),

    dict(ref="CF-2026-000009",
         title="Large pothole on Aundh-Rahatani Road",
         desc="A pothole about 50 cm wide has formed on the Aundh-Rahatani main road. "
              "Rush-hour traffic is severely affected.",
         cat=CategoryEnum.Pothole, status=StatusEnum.InProgress, sev=4,
         addr="Aundh-Rahatani Road, Aundh, Pune 411007",
         lat=18.5652, lng=73.8478, votes=20,
         photos=[P["pothole"]], before_url=P["pothole"], after_url=None,
         team="Roads", days=10, ai=True, parent=None),

    dict(ref="CF-2026-000010",
         title="Road edge crumbling near Deccan bus stop",
         desc="The road edge at Deccan bus stop has crumbled, leaving a 25 cm drop. "
              "Motorcyclists riding close to the kerb are at risk.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Reopened, sev=3,
         addr="Deccan Gymkhana, near Bus Stop, Pune 411004",
         lat=18.5192, lng=73.8468, votes=17,
         photos=[P["pothole2"]], before_url=P["pothole2"], after_url=None,
         team="Roads", days=25, ai=False, parent=None),

    # ── Water Leaks ───────────────────────────────────────────────────────────
    dict(ref="CF-2026-000011",
         title="Burst water main on Prabhat Road",
         desc="A water main has burst on Prabhat Road near Deccan Gymkhana. "
              "Water is gushing out and flooding the footpath. Road surface weakening.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.InProgress, sev=5,
         addr="Prabhat Road, Deccan Gymkhana, Pune 411004",
         lat=18.5192, lng=73.8478, votes=38,
         photos=[P["water"]], before_url=P["water"], after_url=None,
         team="Water", days=9, ai=True, parent=None),

    dict(ref="CF-2026-000012",
         title="Leaking pipe on footpath — Baner Road",
         desc="A roadside pipe on Baner Road is leaking continuously, "
              "wasting ~400 litres per day and creating a slippery footpath.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Assigned, sev=3,
         addr="Baner Road, near D-Mart, Pune 411045",
         lat=18.5580, lng=73.7882, votes=13,
         photos=[P["water"]], before_url=None, after_url=None,
         team="Water", days=5, ai=False, parent=None),

    dict(ref="CF-2026-000013",
         title="Water pooling after roadworks on JM Road",
         desc="Water pools forming after utility roadworks on JM Road. "
              "A drain appears blocked by construction debris.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Resolved, sev=3,
         addr="JM Road, Shivajinagar, Pune 411005",
         lat=18.5249, lng=73.8504, votes=11,
         photos=[P["water"]], before_url=P["water"], after_url=P["pipe_fixed"],
         team="Water", days=22, ai=False, parent=None),

    dict(ref="CF-2026-000014",
         title="Sewage overflow near Hadapsar market",
         desc="Sewage overflowing from a manhole near the main market in Hadapsar. "
              "The stench is unbearable — serious health hazard.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Reported, sev=4,
         addr="Hadapsar Market Road, Pune 411028",
         lat=18.5010, lng=73.9258, votes=24,
         photos=[P["water"]], before_url=None, after_url=None,
         team=None, days=4, ai=True, parent=None),

    dict(ref="CF-2026-000015",
         title="Burst underground pipe near Kothrud municipal garden",
         desc="An underground pipe has burst near the municipal garden in Kothrud. "
              "Water is rising to the surface and seeping into the road base.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Assigned, sev=4,
         addr="Near Municipal Garden, Kothrud, Pune 411038",
         lat=18.5050, lng=73.8100, votes=19,
         photos=[P["water"]], before_url=None, after_url=None,
         team="Water", days=7, ai=False, parent=None),

    dict(ref="CF-2026-000016",
         title="Severe waterlogging at Katraj underpass",
         desc="Katraj underpass floods every time it rains. Drainage completely choked. "
              "Vehicles have stalled here multiple times — critical risk to commuters.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.InProgress, sev=5,
         addr="Katraj Underpass, Swargate-Katraj Road, Pune 411046",
         lat=18.4524, lng=73.8560, votes=42,
         photos=[P["water"]], before_url=P["water"], after_url=None,
         team="Water", days=11, ai=True, parent=None),

    dict(ref="CF-2026-000017",
         title="Drain overflow in Viman Nagar residential lane",
         desc="The drain in Lane 7, Viman Nagar is overflowing onto the footpath "
              "after recent rains. Residents cannot use the footpath.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Reported, sev=2,
         addr="Lane 7, Viman Nagar, Pune 411014",
         lat=18.5670, lng=73.9155, votes=8,
         photos=[P["water"]], before_url=None, after_url=None,
         team=None, days=1, ai=False, parent=None),

    dict(ref="CF-2026-000018",
         title="Water pipeline leak near Shivajinagar temple",
         desc="A water distribution pipeline behind the temple on Shivaji Road is leaking. "
              "Around 600 litres per day wasted.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Resolved, sev=3,
         addr="Shivaji Road, near Temple, Shivajinagar, Pune 411016",
         lat=18.5295, lng=73.8450, votes=14,
         photos=[P["water"]], before_url=P["water"], after_url=P["pipe_fixed"],
         team="Water", days=33, ai=False, parent=None),

    # ── Garbage ───────────────────────────────────────────────────────────────
    dict(ref="CF-2026-000019",
         title="Community bin overflowing — Lane 5, Kothrud",
         desc="The community dustbin at Lane 5, Kothrud has been overflowing for 3 days. "
              "Garbage spilling onto the lane and attracting stray dogs.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Resolved, sev=2,
         addr="Lane 5, Kothrud, Pune 411038",
         lat=18.5080, lng=73.8090, votes=19,
         photos=[P["garbage"]], before_url=P["garbage"], after_url=P["area_clean"],
         team="Sanitation & Electrical", days=40, ai=False, parent=None),

    dict(ref="CF-2026-000020",
         title="Garbage dumped on footpath near Hadapsar IT Park",
         desc="Construction and household waste illegally dumped on the footpath "
              "near the IT park in Hadapsar. Pedestrians forced onto the road.",
         cat=CategoryEnum.Garbage, status=StatusEnum.InProgress, sev=3,
         addr="Near Hadapsar IT Park, Pune 411028",
         lat=18.5020, lng=73.9280, votes=22,
         photos=[P["garbage"]], before_url=P["garbage"], after_url=None,
         team="Sanitation & Electrical", days=13, ai=True, parent=None),

    dict(ref="CF-2026-000021",
         title="Garbage collection skipped — Viman Nagar Lane 3",
         desc="Lane 3 in Viman Nagar skipped during garbage collection for 4 consecutive days. "
              "Waste piling up outside homes.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Resolved, sev=2,
         addr="Lane 3, Viman Nagar, Pune 411014",
         lat=18.5679, lng=73.9138, votes=21,
         photos=[P["garbage"]], before_url=P["garbage"], after_url=P["area_clean"],
         team="Sanitation & Electrical", days=44, ai=False, parent=None),

    dict(ref="CF-2026-000022",
         title="Open garbage dump near Katraj nullah",
         desc="An open garbage dump has formed near the nullah at Katraj. "
              "Burning of waste occurring. Health and air quality concerns.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Reported, sev=4,
         addr="Katraj, near NH-48 nullah, Pune 411046",
         lat=18.4530, lng=73.8590, votes=29,
         photos=[P["garbage"]], before_url=None, after_url=None,
         team=None, days=5, ai=True, parent=None),

    dict(ref="CF-2026-000023",
         title="Construction debris on Sinhagad Road footpath",
         desc="Construction waste from a nearby site dumped on the public footpath "
              "near Sinhagad Road junction. Pedestrians cannot use the path.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Reported, sev=2,
         addr="Sinhagad Road Junction, Dattawadi, Pune 411030",
         lat=18.4840, lng=73.8350, votes=7,
         photos=[P["construction"]], before_url=None, after_url=None,
         team=None, days=2, ai=False, parent=None),

    dict(ref="CF-2026-000024",
         title="Overflowing municipal bin — Aundh main junction",
         desc="The municipal bin at the Aundh-Rahatani junction has been overflowing "
              "for 2 days. Waste spilling onto the main road.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Assigned, sev=3,
         addr="Aundh-Rahatani Road Junction, Aundh, Pune 411007",
         lat=18.5645, lng=73.8472, votes=16,
         photos=[P["garbage"]], before_url=None, after_url=None,
         team="Sanitation & Electrical", days=8, ai=False, parent=None),

    dict(ref="CF-2026-000025",
         title="Illegal garbage dumping near Baner lake",
         desc="Household waste being dumped on the Baner lake embankment. "
              "Polluting the water body and harming wildlife.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Reported, sev=3,
         addr="Baner Lake Embankment, Baner, Pune 411045",
         lat=18.5600, lng=73.7850, votes=11,
         photos=[P["garbage"]], before_url=None, after_url=None,
         team=None, days=3, ai=True, parent=None),

    # ── Streetlights ──────────────────────────────────────────────────────────
    dict(ref="CF-2026-000026",
         title="Three consecutive streetlights out on FC Road",
         desc="Three streetlights near the Shivajinagar bus stand on FC Road have "
              "been non-functional for 5 nights. The stretch is extremely dark and unsafe.",
         cat=CategoryEnum.Streetlight, status=StatusEnum.Assigned, sev=3,
         addr="FC Road, near Bus Stand, Shivajinagar, Pune 411016",
         lat=18.5308, lng=73.8490, votes=23,
         photos=[P["streetlight"]], before_url=None, after_url=None,
         team="Sanitation & Electrical", days=10, ai=False, parent=None),

    dict(ref="CF-2026-000027",
         title="Footpath streetlight dead — Shivajinagar court road",
         desc="The streetlight on the pedestrian footpath near the court on "
              "Shivajinagar Road has been dead for a week. Women feel unsafe at night.",
         cat=CategoryEnum.Streetlight, status=StatusEnum.Reported, sev=3,
         addr="Shivajinagar Road, near District Court, Pune 411005",
         lat=18.5298, lng=73.8480, votes=8,
         photos=[P["streetlight"]], before_url=None, after_url=None,
         team=None, days=4, ai=False, parent=None),

    dict(ref="CF-2026-000028",
         title="Two streetlights broken — Paud Road, Kothrud",
         desc="Two consecutive streetlights on Paud Road, Kothrud have been out "
              "for a week. The area has seen chain-snatching incidents.",
         cat=CategoryEnum.Streetlight, status=StatusEnum.Assigned, sev=3,
         addr="Paud Road, Kothrud, Pune 411038",
         lat=18.4976, lng=73.8180, votes=23,
         photos=[P["streetlight"]], before_url=None, after_url=None,
         team="Sanitation & Electrical", days=12, ai=False, parent=None),

    dict(ref="CF-2026-000029",
         title="Street lamp broken near Hadapsar primary school",
         desc="Street lamp in front of the primary school on Hadapsar Main Road is broken. "
              "Students leaving after evening tuitions are at risk.",
         cat=CategoryEnum.Streetlight, status=StatusEnum.Resolved, sev=2,
         addr="Hadapsar Main Road, near Primary School, Pune 411028",
         lat=18.5025, lng=73.9265, votes=16,
         photos=[P["streetlight"]],
         before_url=P["streetlight"], after_url=P["area_clean"],
         team="Sanitation & Electrical", days=28, ai=False, parent=None),

    dict(ref="CF-2026-000030",
         title="Dark stretch — Viman Nagar to Kharadi connector road",
         desc="The entire connector road from Viman Nagar to Kharadi has no working "
              "streetlights. Used heavily by IT employees on night shifts.",
         cat=CategoryEnum.Streetlight, status=StatusEnum.InProgress, sev=3,
         addr="Viman Nagar-Kharadi Connector Road, Pune 411014",
         lat=18.5668, lng=73.9150, votes=14,
         photos=[P["streetlight"]], before_url=P["streetlight"], after_url=None,
         team="Sanitation & Electrical", days=14, ai=True, parent=None),

    # ── Other ─────────────────────────────────────────────────────────────────
    dict(ref="CF-2026-000031",
         title="Open drain cover on JM Road — serious safety hazard",
         desc="A drain cover on JM Road crossing is missing. The open drain is 60 cm deep. "
              "Highly dangerous at night. A resident's scooter fell in yesterday.",
         cat=CategoryEnum.Other, status=StatusEnum.Reopened, sev=5,
         addr="JM Road Crossing, Pune 411005",
         lat=18.5249, lng=73.8504, votes=42,
         photos=[P["drain"]], before_url=P["drain"], after_url=None,
         team="Roads", days=20, ai=True, parent=None),

    dict(ref="CF-2026-000032",
         title="Fallen tree blocking Baner Road after storm",
         desc="A large tree fell on Baner Road after last night's storm, "
              "blocking one full lane. Emergency clearance required.",
         cat=CategoryEnum.Other, status=StatusEnum.Resolved, sev=4,
         addr="Baner Road, near Seasons Hotel, Pune 411045",
         lat=18.5585, lng=73.7875, votes=33,
         photos=[P["construction"]],
         before_url=P["construction"], after_url=P["road_fixed"],
         team="Roads", days=35, ai=False, parent=None),

    dict(ref="CF-2026-000033",
         title="Broken footpath tiles near Deccan Gymkhana market",
         desc="Several footpath tiles near the Deccan market are broken and uneven. "
              "Elderly residents have tripped multiple times.",
         cat=CategoryEnum.Other, status=StatusEnum.Reported, sev=2,
         addr="Deccan Gymkhana, near Market, Pune 411004",
         lat=18.5185, lng=73.8460, votes=9,
         photos=[P["construction"]], before_url=None, after_url=None,
         team=None, days=6, ai=False, parent=None),

    dict(ref="CF-2026-000034",
         title="Footpath encroachment by vendor stalls — Aundh ITI Road",
         desc="Vendor stalls occupying the entire footpath near Aundh-ITI Road "
              "for the last 2 weeks. Pedestrians are walking on the road.",
         cat=CategoryEnum.Other, status=StatusEnum.Assigned, sev=3,
         addr="Aundh-ITI Road, Aundh, Pune 411007",
         lat=18.5640, lng=73.8485, votes=15,
         photos=[P["construction"]], before_url=None, after_url=None,
         team="Roads", days=9, ai=False, parent=None),

    dict(ref="CF-2026-000035",
         title="Damaged footpath near Katraj vegetable market",
         desc="Footpath in front of the vegetable market in Katraj has missing tiles "
              "and exposed rebar. Risk of serious injury.",
         cat=CategoryEnum.Other, status=StatusEnum.Reported, sev=2,
         addr="Katraj Vegetable Market, Pune 411046",
         lat=18.4520, lng=73.8565, votes=6,
         photos=[P["construction"]], before_url=None, after_url=None,
         team=None, days=3, ai=False, parent=None),

    # ── Duplicates (linked to parent issues) ──────────────────────────────────
    dict(ref="CF-2026-000036",
         title="Duplicate — Pothole still unfixed on Karve Road near Nal Stop",
         desc="Same large pothole as CF-2026-000001 — still not repaired. "
              "Filing again as situation has worsened after rain.",
         cat=CategoryEnum.Pothole, status=StatusEnum.Reported, sev=3,
         addr="Karve Road, near Nal Stop, Kothrud, Pune 411038",
         lat=18.5076, lng=73.8079, votes=5,
         photos=[P["pothole"]], before_url=None, after_url=None,
         team=None, days=14, ai=False, parent="CF-2026-000001"),

    dict(ref="CF-2026-000037",
         title="Duplicate — Water burst on Prabhat Road still active",
         desc="The water main burst (CF-2026-000011) on Prabhat Road is still active. "
              "Submitting again as the original report may not have been acted on.",
         cat=CategoryEnum.WaterLeak, status=StatusEnum.Reported, sev=4,
         addr="Prabhat Road, Deccan Gymkhana, Pune 411004",
         lat=18.5191, lng=73.8479, votes=6,
         photos=[P["water"]], before_url=None, after_url=None,
         team=None, days=8, ai=False, parent="CF-2026-000011"),

    dict(ref="CF-2026-000038",
         title="Duplicate — Overflowing bin, Lane 5, Kothrud (residual waste)",
         desc="Partial cleanup done for CF-2026-000019 but residual waste remains. "
              "Filing as a follow-up.",
         cat=CategoryEnum.Garbage, status=StatusEnum.Reported, sev=2,
         addr="Lane 5, Kothrud, Pune 411038",
         lat=18.5079, lng=73.8091, votes=3,
         photos=[P["garbage"]], before_url=None, after_url=None,
         team=None, days=38, ai=False, parent="CF-2026-000019"),

    dict(ref="CF-2026-000039",
         title="Duplicate — FC Road streetlights still partially out",
         desc="Two of three streetlights on FC Road (CF-2026-000026) are still not working "
              "after partial repair. Requesting full resolution.",
         cat=CategoryEnum.Streetlight, status=StatusEnum.Reported, sev=3,
         addr="FC Road, near Bus Stand, Shivajinagar, Pune 411016",
         lat=18.5309, lng=73.8491, votes=4,
         photos=[P["streetlight"]], before_url=None, after_url=None,
         team=None, days=9, ai=False, parent="CF-2026-000026"),
]


# ── Status-history builder ─────────────────────────────────────────────────────

STATUS_NOTES = {
    # (status, category_group) → note text
    ("Reported",     "road"):    "Issue reported via CivicFix app.",
    ("Reported",     "water"):   "Issue reported via CivicFix app.",
    ("Reported",     "garbage"): "Issue reported via CivicFix app.",
    ("Reported",     "light"):   "Issue reported via CivicFix app.",
    ("Reported",     "other"):   "Issue reported via CivicFix app.",
    ("Assigned",     "road"):    "Assigned to Roads team for inspection.",
    ("Assigned",     "water"):   "Assigned to Water Supply team.",
    ("Assigned",     "garbage"): "Assigned to Sanitation & Electrical team.",
    ("Assigned",     "light"):   "Assigned to Sanitation & Electrical team.",
    ("Assigned",     "other"):   "Assigned to Roads team.",
    ("In Progress",  "road"):    "Repair crew deployed. Patching work underway.",
    ("In Progress",  "water"):   "Plumbing crew on site. Pipe isolation in progress.",
    ("In Progress",  "garbage"): "Collection vehicle scheduled. Clearance in progress.",
    ("In Progress",  "light"):   "Electrical team on site. Replacement parts sourced.",
    ("In Progress",  "other"):   "Field crew dispatched. Issue being addressed.",
    ("Resolved",     "road"):    "Pothole filled and road surface levelled. Site cleared.",
    ("Resolved",     "water"):   "Leak repaired and pipe pressure restored. Area cleared.",
    ("Resolved",     "garbage"): "Site cleared, sanitised, and bin replaced.",
    ("Resolved",     "light"):   "Streetlight replaced and tested. Operational.",
    ("Resolved",     "other"):   "Issue resolved. Site inspected and cleared.",
    ("Reopened",     "any"):     "Problem has recurred. Requesting re-inspection.",
}


def _cat_group(cat: CategoryEnum) -> str:
    return {
        CategoryEnum.Pothole:    "road",
        CategoryEnum.WaterLeak:  "water",
        CategoryEnum.Garbage:    "garbage",
        CategoryEnum.Streetlight:"light",
        CategoryEnum.Other:      "other",
    }[cat]


def build_history(
    spec: dict,
    citizen_id: int,
    worker_id: int,
    created_at: datetime,
) -> list[dict]:
    """Return a list of StatusHistory field-dicts for the given issue spec."""
    status  = spec["status"]
    cg      = _cat_group(spec["cat"])
    ph_first = spec["photos"][0] if spec["photos"] else None

    flow = [StatusEnum.Reported]
    if status in (StatusEnum.Assigned, StatusEnum.InProgress,
                  StatusEnum.Resolved, StatusEnum.Reopened):
        flow.append(StatusEnum.Assigned)
    if status in (StatusEnum.InProgress, StatusEnum.Resolved, StatusEnum.Reopened):
        flow.append(StatusEnum.InProgress)
    if status in (StatusEnum.Resolved, StatusEnum.Reopened):
        flow.append(StatusEnum.Resolved)
    if status == StatusEnum.Reopened:
        flow.append(StatusEnum.Reopened)

    offsets = {
        StatusEnum.Reported:   timedelta(0),
        StatusEnum.Assigned:   timedelta(hours=20),
        StatusEnum.InProgress: timedelta(days=2),
        StatusEnum.Resolved:   timedelta(days=5),
        StatusEnum.Reopened:   timedelta(days=8),
    }

    rows = []
    for s in flow:
        if s == StatusEnum.Reported:
            actor_role = "citizen"
            changed_by = citizen_id
            photo_url  = ph_first
        elif s == StatusEnum.Assigned:
            actor_role = "system"
            changed_by = None
            photo_url  = None
        elif s in (StatusEnum.InProgress, StatusEnum.Resolved):
            actor_role = "worker"
            changed_by = worker_id
            photo_url  = spec["after_url"] if s == StatusEnum.Resolved else None
        else:  # Reopened
            actor_role = "citizen"
            changed_by = citizen_id
            photo_url  = None

        note_key = (s.value, cg if s != StatusEnum.Reopened else "any")
        note = STATUS_NOTES.get(note_key, STATUS_NOTES.get((s.value, "other"), ""))

        rows.append(dict(
            status     = s,
            note       = note,
            photo_url  = photo_url,
            actor_role = actor_role,
            changed_by = changed_by,
            created_at = created_at + offsets[s],
        ))
    return rows


# ── Seed functions ─────────────────────────────────────────────────────────────

def seed_teams(db) -> dict[str, Team]:
    team_map: dict[str, Team] = {}
    for td in TEAMS_DATA:
        existing = db.query(Team).filter(Team.name == td["name"]).first()
        if existing:
            print(f"  [skip] team '{td['name']}' already exists")
            team_map[td["name"]] = existing
        else:
            t = Team(name=td["name"], categories=td["categories"])
            db.add(t)
            db.flush()          # get t.id without committing
            print(f"  [+] team '{td['name']}'")
            team_map[td["name"]] = t
    return team_map


def seed_users(db, team_map: dict[str, Team]) -> dict[str, User]:
    user_map: dict[str, User] = {}
    hashed = _hash_password(DEMO_PASSWORD)
    for ud in USERS_DATA:
        existing = db.query(User).filter(User.email == ud["email"]).first()
        if existing:
            print(f"  [skip] user '{ud['email']}' already exists")
            user_map[ud["email"]] = existing
        else:
            team_id = team_map[ud["team"]].id if ud["team"] else None
            u = User(
                name          = ud["name"],
                email         = ud["email"],
                password_hash = hashed,
                role          = ud["role"],
                team_id       = team_id,
            )
            db.add(u)
            db.flush()
            print(f"  [+] user '{ud['email']}' ({ud['role']})")
            user_map[ud["email"]] = u
    return user_map


def seed_issues(
    db,
    team_map: dict[str, Team],
    citizen: User,
    worker: User,
) -> None:
    # First pass — insert all non-duplicate issues so parent IDs exist
    ref_to_db: dict[str, Issue] = {}

    for spec in ISSUES_DATA:
        existing = db.query(Issue).filter(Issue.reference_id == spec["ref"]).first()
        if existing:
            print(f"  [skip] issue {spec['ref']} already exists")
            ref_to_db[spec["ref"]] = existing
            continue

        days      = spec["days"]
        created   = utc(days_ago=days, hour=9, minute=30)
        team_obj  = team_map.get(spec["team"]) if spec["team"] else None

        # Resolve parent (must already be in DB or in ref_to_db from this run)
        parent_db_id: int | None = None
        if spec["parent"]:
            parent_obj = ref_to_db.get(spec["parent"]) or \
                         db.query(Issue).filter(Issue.reference_id == spec["parent"]).first()
            if parent_obj:
                parent_db_id = parent_obj.id

        votes  = spec["votes"]

        # resolved_at for resolved/reopened issues
        resolved_at = None
        if spec["status"] in (StatusEnum.Resolved, StatusEnum.Reopened):
            resolved_at = created + timedelta(days=5)

        issue = Issue(
            reference_id    = spec["ref"],
            title           = spec["title"],
            description     = spec["desc"],
            category        = spec["cat"],
            status          = spec["status"],
            severity        = spec["sev"],
            community_impact= votes,
            affected_count  = votes,
            priority_score  = 0.0,          # computed below after flush
            address         = spec["addr"],
            lat             = spec["lat"],
            lng             = spec["lng"],
            team_id         = team_obj.id if team_obj else None,
            reporter_id     = citizen.id,
            parent_issue_id = parent_db_id,
            duplicate_score = 0.92 if parent_db_id else None,
            created_at      = created,
            resolved_at     = resolved_at,
        )
        db.add(issue)
        db.flush()          # get issue.id

        # IssuePhoto rows
        for url in spec["photos"]:
            db.add(IssuePhoto(issue_id=issue.id, url=url, kind=PhotoKindEnum.before,
                              created_at=created))
        if spec["after_url"]:
            db.add(IssuePhoto(issue_id=issue.id, url=spec["after_url"],
                              kind=PhotoKindEnum.after, created_at=created + timedelta(days=5)))

        # StatusHistory rows
        for h in build_history(spec, citizen.id, worker.id, created):
            db.add(StatusHistory(
                issue_id   = issue.id,
                status     = h["status"],
                note       = h["note"],
                photo_url  = h["photo_url"],
                actor_role = h["actor_role"],
                changed_by = h["changed_by"],
                created_at = h["created_at"],
            ))

        # Compute real priority score now that issue has id + created_at
        issue.priority_score = compute_priority_score_for_seed(issue)
        db.add(issue)

        ref_to_db[spec["ref"]] = issue
        print(f"  [+] issue {spec['ref']} — {spec['status'].value} — {spec['title'][:55]}")


def seed_notifications(db, citizen: User) -> None:
    """Seed a few sample notifications for the citizen demo account."""
    if db.query(Notification).filter(Notification.user_id == citizen.id).count() > 0:
        print("  [skip] notifications for citizen already exist")
        return

    msgs = [
        ("Your pothole report on Karve Road has been assigned to the Roads team.", False),
        ("Water leak on Prabhat Road is now In Progress.", False),
        ("Your report CF-2026-000019 was resolved. Please confirm satisfaction.", True),
    ]

    # Try to link to real issues where possible
    issue_refs = ["CF-2026-000001", "CF-2026-000011", "CF-2026-000019"]
    for i, (msg, read) in enumerate(msgs):
        issue = db.query(Issue).filter(Issue.reference_id == issue_refs[i]).first()
        db.add(Notification(
            user_id    = citizen.id,
            issue_id   = issue.id if issue else None,
            message    = msg,
            is_read    = read,
            created_at = datetime.now(UTC) - timedelta(hours=[2, 26, 74][i]),
        ))
    print(f"  [+] {len(msgs)} notifications for citizen")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    print("▶ Creating / verifying tables …")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("\n▶ Seeding teams …")
        team_map = seed_teams(db)

        print("\n▶ Seeding users …")
        user_map = seed_users(db, team_map)

        citizen = user_map["citizen@demo.com"]
        worker  = user_map["worker@demo.com"]

        print("\n▶ Seeding issues (39 total) …")
        seed_issues(db, team_map, citizen, worker)

        print("\n▶ Seeding notifications …")
        seed_notifications(db, citizen)

        db.commit()
        print("\n✅  Seed complete — all rows committed.")

        # Summary query
        from sqlalchemy import text
        for tbl in ("teams", "users", "issues", "issue_photos",
                    "status_history", "notifications"):
            count = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"   {tbl:<20} {count:>4} row(s)")

    except Exception as exc:
        db.rollback()
        print(f"\n❌  Seed failed — rolled back. Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
