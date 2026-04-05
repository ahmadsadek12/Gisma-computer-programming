"""Local authentication: signup and login."""

from __future__ import annotations

from datetime import datetime, timezone

from data.database_manager import DatabaseManager
from models.user import User
from utils.security import hash_password, verify_password
from utils import validators


class AuthService:
    """Signup, login validation, and user records in SQLite."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def signup(
        self, username: str, email: str, password: str, confirm: str
    ) -> User:
        ok, msg = validators.validate_username(username)
        if not ok:
            raise ValueError(msg)
        ok, msg = validators.validate_email(email)
        if not ok:
            raise ValueError(msg)
        ok, msg = validators.validate_password(password)
        if not ok:
            raise ValueError(msg)
        ok, msg = validators.passwords_match(password, confirm)
        if not ok:
            raise ValueError(msg)

        ph = hash_password(password)
        now = datetime.now(timezone.utc).isoformat()
        uid = self._db.create_user(
            username.strip(), email.strip().lower(), ph, now
        )
        row = self._db.get_user_by_id(uid)
        if not row:
            raise RuntimeError("User could not be loaded after signup.")
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            created_at=row["created_at"],
        )

    def login(self, username_or_email: str, password: str) -> User:
        raw = (username_or_email or "").strip()
        pw = password or ""
        if not raw:
            raise ValueError("Please enter your username or email.")
        if not pw.strip():
            raise ValueError("Please enter your password.")

        row = self._db.get_user_by_username(raw)
        if not row and "@" in raw:
            row = self._db.get_user_by_email(raw.lower())
        if not row:
            if "@" in raw:
                raise ValueError(
                    "No account is registered with this email address. "
                    "Check the spelling or sign up."
                )
            raise ValueError(
                "No account found for this username. Check the spelling or sign up."
            )
        if not verify_password(pw, row["password_hash"]):
            raise ValueError("Incorrect password. Please try again.")

        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            created_at=row["created_at"],
        )
