"""User model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    """Local application user."""

    id: int
    username: str
    email: str
    created_at: str
