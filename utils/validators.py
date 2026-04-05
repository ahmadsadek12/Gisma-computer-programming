"""Simple input validation for signup and forms."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_username(username: str) -> tuple[bool, str]:
    u = username.strip()
    if len(u) < 3:
        return False, "Username must be at least 3 characters."
    if len(u) > 64:
        return False, "Username is too long."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", u):
        return False, "Username may only contain letters, digits, ._-"
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    e = email.strip()
    if len(e) > 254:
        return False, "Email is too long."
    if not _EMAIL_RE.match(e):
        return False, "Please enter a valid email address."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if len(password) > 256:
        return False, "Password is too long."
    return True, ""


def passwords_match(password: str, confirm: str) -> tuple[bool, str]:
    if password != confirm:
        return False, "Passwords do not match."
    return True, ""
