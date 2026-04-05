"""Password hashing using PBKDF2-HMAC-SHA256."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets

_ITERATIONS = 390_000
_SALT_BYTES = 16


def hash_password(plain: str) -> str:
    """
    Return a storable string: pbkdf2$<iter>$<salt_b64>$<hash_b64>
    """
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256", plain.encode("utf-8"), salt, _ITERATIONS
    )
    return (
        f"pbkdf2${_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(dk).decode('ascii')}"
    )


def verify_password(plain: str, stored: str) -> bool:
    """Verify plain password against stored hash string."""
    try:
        parts = stored.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2":
            return False
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2].encode("ascii"))
        expected = base64.b64decode(parts[3].encode("ascii"))
        dk = hashlib.pbkdf2_hmac(
            "sha256", plain.encode("utf-8"), salt, iterations
        )
        return secrets.compare_digest(dk, expected)
    except (ValueError, TypeError, IndexError):
        return False
