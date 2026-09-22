"""Provision the single administrator account.

This is the ONLY way an admin comes into existence from nothing; the public
registration endpoint cannot create one. Idempotent — safe to re-run.

    ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='...' python -m scripts.seed_admin

Re-running with a different ADMIN_PASSWORD resets that admin's password.
"""
import sys

from app.core.config import ADMIN_EMAIL, ADMIN_FULLNAME, ADMIN_PASSWORD
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole

MIN_PASSWORD_LEN = 12


def main() -> int:
    if not ADMIN_EMAIL or not ADMIN_EMAIL.strip():
        print("ADMIN_EMAIL is not set. Refusing to run.", file=sys.stderr)
        return 1

    if not ADMIN_PASSWORD or len(ADMIN_PASSWORD) < MIN_PASSWORD_LEN:
        print(
            f"ADMIN_PASSWORD must be set and at least {MIN_PASSWORD_LEN} characters. "
            "Refusing to run.",
            file=sys.stderr,
        )
        return 1

    email = ADMIN_EMAIL.strip().lower()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()

        if existing:
            existing.role = UserRole.ADMIN
            existing.is_active = True
            existing.password = hash_password(ADMIN_PASSWORD)
            db.commit()
            print(f"Updated existing account {email} to ADMIN and reset its password.")
        else:
            db.add(
                User(
                    fullname=ADMIN_FULLNAME,
                    email=email,
                    password=hash_password(ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            db.commit()
            print(f"Created ADMIN account {email}.")

        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        print(f"Admin accounts now present ({len(admins)}):")
        for a in admins:
            print(f"  - {a.email} (active={a.is_active})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
