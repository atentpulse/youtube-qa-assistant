"""
Operational Admin Bootstrap Script
Provides secure administrative bootstrapping without public endpoints or hardcoded credentials.

Usage:
    python backend/scripts/bootstrap_admin.py promote --email admin@example.com
    python backend/scripts/bootstrap_admin.py create --email admin@example.com --username Admin --password <secret>
"""
import argparse
import sys
import os

# Add parent directory to sys.path so app modules can be loaded when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.database import SessionLocal
from app.models.user import User
from app.auth.password import hash_password


def promote_user(email: str, db=None) -> bool:
    email_clean = email.strip().lower()
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        user = db.query(User).filter(User.email == email_clean).first()
        if not user:
            print(f"Error: User with email '{email_clean}' not found.", file=sys.stderr)
            return False
        user.role = "admin"
        db.commit()
        print(f"Success: User '{email_clean}' (ID={user.id}) has been promoted to 'admin'.")
        return True
    finally:
        if close_db:
            db.close()


def create_admin(email: str, username: str, password: str, db=None) -> bool:
    email_clean = email.strip().lower()
    username_clean = username.strip()
    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.", file=sys.stderr)
        return False

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        existing = db.query(User).filter(User.email == email_clean).first()
        if existing:
            print(f"Error: User with email '{email_clean}' already exists.", file=sys.stderr)
            return False

        hashed = hash_password(password)
        admin_user = User(
            email=email_clean,
            username=username_clean,
            password_hash=hashed,
            auth_provider="local",
            email_verified=True,
            role="admin",
            token_version=1,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Success: Created new admin user '{email_clean}' (ID={admin_user.id}).")
        return True
    finally:
        if close_db:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Operational Admin Bootstrap CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Promote subcommand
    promote_parser = subparsers.add_parser("promote", help="Promote an existing user to admin")
    promote_parser.add_argument("--email", required=True, help="Email of the existing user")

    # Create subcommand
    create_parser = subparsers.add_parser("create", help="Create a new administrator account")
    create_parser.add_argument("--email", required=True, help="Email for the admin account")
    create_parser.add_argument("--username", required=True, help="Username for the admin account")
    create_parser.add_argument("--password", required=True, help="Password for the admin account")

    args = parser.parse_args()

    if args.command == "promote":
        success = promote_user(args.email)
        sys.exit(0 if success else 1)
    elif args.command == "create":
        success = create_admin(args.email, args.username, args.password)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
