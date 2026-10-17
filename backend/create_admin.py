"""
Create an admin (or worker) account directly in the database.
Usage:
  python create_admin.py
"""
import sys
sys.path.insert(0, ".")

from app.core.database import get_db
from app.core.security import hash_password
from app.models import User, RoleEnum

NAME     = "Admin User"
EMAIL    = "admin@civicfix.com"
PASSWORD = "Admin1234"
ROLE     = RoleEnum.admin   # change to RoleEnum.worker for a worker account

db = next(get_db())

existing = db.query(User).filter(User.email == EMAIL).first()
if existing:
    # Just upgrade the role if the user already exists
    existing.role = ROLE
    db.commit()
    print(f"Updated existing user '{EMAIL}' -> role={ROLE.value}")
else:
    user = User(
        name=NAME,
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        role=ROLE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created {ROLE.value} account:")

print(f"  Email   : {EMAIL}")
print(f"  Password: {PASSWORD}")
print(f"  Role    : {ROLE.value}")
print("Login at http://localhost:5173/login")
