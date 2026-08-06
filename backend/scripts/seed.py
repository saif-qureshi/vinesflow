"""Seed the permission catalog and (optionally) a demo user + org.

Run with:  uv run python -m scripts.seed
Idempotent: safe to run multiple times.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.orgs.service import OrgService
from app.modules.rbac.service import RbacService
from app.modules.users.models import User

DEMO_EMAIL = "admin@vineflow.app"
DEMO_PASSWORD = "password123"
DEMO_ORG = "Demo Company"


def main() -> None:
    db = SessionLocal()
    try:
        RbacService(db).seed_permissions()
        db.commit()
        print("✓ Permission catalog seeded")

        if settings.ENVIRONMENT == "production":
            print("• Skipping the demo account in production")
            return

        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                full_name="Demo Admin",
                hashed_password=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            db.flush()
            OrgService(db).create_org_with_owner(owner=user, name=DEMO_ORG)
            db.commit()
            print(f"✓ Demo user created: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print(f"• Demo user already exists: {DEMO_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
